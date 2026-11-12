"""Turn Python source into a tree of :class:`Symbol` objects.

Only the standard library is used: :mod:`ast` for structure, :mod:`tokenize`
for encoding detection.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import tokenize
from typing import List

from .model import FileModel, StructDiffError, Symbol

_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def read_source(path: str) -> str:
    """Read a Python file, honouring PEP 263 encoding cookies and BOMs."""
    try:
        with tokenize.open(path) as fh:
            return fh.read()
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise StructDiffError(f"cannot read {path}: {exc}") from exc


def parse_source(source: str, path: str = "<source>", label: str = "") -> FileModel:
    """Parse ``source`` into a :class:`FileModel`.

    Raises :class:`StructDiffError` with a readable message on syntax errors.
    """
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        snippet = (exc.text or "").rstrip()
        where = f"{path}:{exc.lineno}" if exc.lineno else path
        message = f"{where}: syntax error: {exc.msg}"
        if snippet:
            message += f"\n    {snippet.strip()}"
        raise StructDiffError(message) from exc
    except ValueError as exc:  # e.g. source containing null bytes
        raise StructDiffError(f"{path}: cannot parse: {exc}") from exc

    lines = source.splitlines()
    symbols: List[Symbol] = []
    _collect(tree.body, symbols, depth=0, prefix="", parent_kind="module", lines=lines)

    return FileModel(
        path=path,
        label=label or path,
        source=source,
        lines=lines,
        symbols=symbols,
        loc=_count_loc(lines, 1, len(lines)),
    )


def parse_file(path: str, label: str = "") -> FileModel:
    return parse_source(read_source(path), path=path, label=label or path)


def _collect(
    body: List[ast.stmt],
    out: List[Symbol],
    depth: int,
    prefix: str,
    parent_kind: str,
    lines: List[str],
) -> None:
    for node in body:
        if not isinstance(node, _DEF_TYPES):
            continue

        end_lineno = getattr(node, "end_lineno", None) or node.lineno
        qualname = f"{prefix}{node.name}"

        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif parent_kind == "class":
            kind = "method"
        elif depth == 0:
            kind = "function"
        else:
            kind = "nested"

        symbol = Symbol(
            kind=kind,
            name=node.name,
            qualname=qualname,
            lineno=node.lineno,
            end_lineno=end_lineno,
            depth=depth,
            loc=_count_loc(lines, node.lineno, end_lineno),
            complexity=_complexity(node),
            params=0 if isinstance(node, ast.ClassDef) else _param_count(node),
            decorators=[ast.unparse(d) for d in node.decorator_list],
            has_doc=ast.get_docstring(node) is not None,
            body_hash=_body_hash(node),
        )
        out.append(symbol)
        _collect(node.body, symbol.children, depth + 1, qualname + ".", kind, lines)


def _count_loc(lines: List[str], start: int, end: int) -> int:
    """Count lines that are neither blank nor comment-only."""
    total = 0
    for index in range(start - 1, min(end, len(lines))):
        text = lines[index].strip()
        if text and not text.startswith("#"):
            total += 1
    return total


def _param_count(node: ast.AST) -> int:
    args = getattr(node, "args", None)
    if not isinstance(args, ast.arguments):
        return 0
    count = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    return count


def _body_hash(node: ast.AST) -> str:
    """Hash a definition's shape, ignoring its name, line numbers and formatting.

    Two functions that differ only by name hash the same, which is what lets
    the matcher recognise a rename instead of a delete + add.
    """
    clone = copy.copy(node)
    if hasattr(clone, "name"):
        clone.name = "\x00"  # type: ignore[attr-defined]
    return hashlib.sha1(ast.dump(clone).encode("utf-8")).hexdigest()


def _complexity(node: ast.AST) -> int:
    """McCabe-style cyclomatic complexity (base 1)."""
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler),
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            score += len(child.ifs)
        elif hasattr(ast, "Match") and isinstance(child, ast.Match):  # type: ignore[attr-defined]
            score += len(child.cases)
    return score
