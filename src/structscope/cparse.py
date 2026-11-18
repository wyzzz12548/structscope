"""Structural parser for brace languages: C, C++, Java, C#, JavaScript.

Python has a real parser in :mod:`ast`; nothing in the standard library
understands C++ or Java.  This module therefore works on *shape* instead of
grammar: it masks comments and string literals, matches braces, and reads each
declaration from the statement that precedes its opening brace.

That is enough to answer the questions StructScope asks — where does each
function start and end, how deeply is it nested, how many decisions does it
make — and it degrades gracefully on unusual syntax instead of refusing to
parse the file.
"""

from __future__ import annotations

import bisect
import hashlib
import re
from typing import Dict, List, Optional, Tuple

from .model import FileModel, Symbol

_KEYWORDS = frozenset(
    """
    if else for while switch case default do return break continue goto
    catch try finally throw throws new delete sizeof typeof instanceof
    synchronized static_cast dynamic_cast const_cast reinterpret_cast
    operator using namespace template typename typedef struct class union
    enum interface public private protected sealed abstract final override
    super this null true false and or not
    """.split()
)

_CONTAINER_RE = re.compile(
    r"\b(class|struct|interface|enum|namespace|union|trait|record)\s+"
    r"([A-Za-z_]\w*)"
)

_DECL_RE = re.compile(
    r"(?s)\A(?P<head>.*?)\b(?P<name>[A-Za-z_]\w*)\s*"
    r"\((?P<params>[^()]*)\)\s*(?P<tail>.*)\Z"
)

_COMPLEXITY_RE = re.compile(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?")

_METHOD_CONTAINERS = frozenset({"class", "struct", "interface", "trait", "record", "union"})


class _Decl:
    __slots__ = ("kind", "name", "open", "close", "lineno", "end_lineno", "params", "body_hash", "is_container", "decorators", "has_doc")

    def __init__(self, kind: str, name: str, open_pos: int, close_pos: int) -> None:
        self.kind = kind
        self.name = name
        self.open = open_pos
        self.close = close_pos
        self.lineno = 0
        self.end_lineno = 0
        self.params = 0
        self.body_hash = ""
        self.is_container = kind not in ("function", "method", "nested")
        self.decorators: List[str] = []
        self.has_doc = False


def mask(source: str) -> str:
    """Blank out comments and string/char literals, keeping line structure.

    Every replaced character becomes a space, newlines are preserved, so line
    numbers and brace positions still line up with the original file.
    """
    out = list(source)
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        pair = source[i : i + 2]
        if pair == "//":
            end = source.find("\n", i)
            if end == -1:
                end = n
            _blank(out, i, end)
            i = end
        elif pair == "/*":
            end = source.find("*/", i + 2)
            end = n if end == -1 else end + 2
            _blank(out, i, end)
            i = end
        elif ch in "\"'":
            end = _literal_end(source, i, ch)
            _blank(out, i, end)
            i = end
        else:
            i += 1
    return "".join(out)


def _blank(out: List[str], start: int, end: int) -> None:
    for k in range(start, min(end, len(out))):
        if out[k] != "\n":
            out[k] = " "


def _literal_end(source: str, start: int, quote: str) -> int:
    i = start + 1
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return i + 1
        if ch == "\n":  # unterminated literal: stop at the line break
            return i
        i += 1
    return n


def parse_c_like(
    source: str,
    path: str = "<source>",
    label: str = "",
    language: str = "cpp",
) -> FileModel:
    """Parse brace-delimited source into a :class:`FileModel`."""
    lines = source.splitlines()
    masked = mask(source)
    line_of = _line_index(masked)
    pairs = _brace_pairs(masked)

    decls: List[_Decl] = []
    decls.extend(_find_containers(masked, pairs, line_of, source))
    decls.extend(_find_functions(masked, pairs, line_of, source, decls))

    symbols = _build_tree(decls, masked, lines, line_of)

    return FileModel(
        path=path,
        label=label or path,
        source=source,
        lines=lines,
        symbols=symbols,
        loc=_count_code_lines(masked, 0, len(lines)),
    )


def _line_index(masked: str) -> List[int]:
    """Offsets of every line start, for O(log n) line lookups."""
    starts = [0]
    for i, ch in enumerate(masked):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_at(starts: List[int], pos: int) -> int:
    return bisect.bisect_right(starts, pos)


def _brace_pairs(masked: str) -> Dict[int, int]:
    pairs: Dict[int, int] = {}
    stack: List[int] = []
    for i, ch in enumerate(masked):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            pairs[stack.pop()] = i
    return pairs


def _statement_start(masked: str, pos: int) -> int:
    j = pos - 1
    while j >= 0 and masked[j] not in ";{}":
        j -= 1
    return j + 1


def _find_containers(
    masked: str, pairs: Dict[int, int], line_of: List[int], source: str
) -> List[_Decl]:
    found: List[_Decl] = []
    for match in _CONTAINER_RE.finditer(masked):
        kind, name = match.group(1), match.group(2)
        brace = _next_brace_before_semicolon(masked, match.end())
        if brace is None:
            continue
        close = pairs.get(brace)
        if close is None:
            continue
        decl = _Decl(kind=kind, name=name, open_pos=brace, close_pos=close)
        decl.lineno = _line_at(line_of, match.start())
        decl.end_lineno = _line_at(line_of, close)
        decl.body_hash = _hash_decl(masked[match.start() : brace], masked, brace, close, name)
        decl.has_doc = _has_doc_before(source, match.start())
        found.append(decl)
    return found


def _next_brace_before_semicolon(masked: str, start: int) -> Optional[int]:
    """Opening brace of a container, skipping a base-class or template list."""
    depth = 0
    i = start
    n = len(masked)
    while i < n:
        ch = masked[i]
        if ch in "<(":
            depth += 1
        elif ch in ">)":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            return None
        elif ch == "{" and depth == 0:
            return i
        i += 1
    return None


def _find_functions(
    masked: str,
    pairs: Dict[int, int],
    line_of: List[int],
    source: str,
    containers: List[_Decl],
) -> List[_Decl]:
    found: List[_Decl] = []
    for open_pos in sorted(pairs):
        close_pos = pairs[open_pos]
        head_start = _statement_start(masked, open_pos)
        segment = masked[head_start:open_pos]
        parsed = _parse_declaration(segment)
        if parsed is None:
            continue
        name, params, decl_offset = parsed
        if name in _KEYWORDS:
            continue
        decl = _Decl(kind="function", name=name, open_pos=open_pos, close_pos=close_pos)
        decl.lineno = _line_at(line_of, head_start + decl_offset)
        decl.end_lineno = _line_at(line_of, close_pos)
        decl.params = _count_top_level_commas(params)
        signature = segment[:decl_offset] + "\x00" + segment[decl_offset + len(name) :]
        decl.body_hash = _hash_decl(signature, masked, open_pos, close_pos, name)
        decl.decorators = _decorators_before(source, head_start + decl_offset)
        decl.has_doc = _has_doc_before(source, head_start + decl_offset)
        found.append(decl)

    return _drop_nested_duplicates(found)


def _parse_declaration(segment: str) -> Optional[Tuple[str, str, int]]:
    """Read ``name (params) qualifiers`` out of the text before a brace."""
    match = _DECL_RE.match(segment)
    if not match:
        return None
    head = match.group("head")
    tail = match.group("tail")
    if "=" in head or "=" in tail:  # assignment, not a declaration
        return None
    if tail.strip() and not re.fullmatch(
        r"[\s\w:,\*&<>\-\[\]\(\)\.]*", tail
    ):  # qualifiers only: const, noexcept, override, throws X, -> T
        return None
    if ";" in head:  # statement boundary was missed
        return None
    stripped_head = head.strip()
    if stripped_head and stripped_head.split()[0] in ("else", "do", "try", "finally"):
        return None
    return match.group("name"), match.group("params"), match.start("name")


def _drop_nested_duplicates(found: List[_Decl]) -> List[_Decl]:
    """Keep the outermost function only: inner blocks are its statements."""
    kept: List[_Decl] = []
    for decl in sorted(found, key=lambda d: d.open):
        if any(k.open < decl.open < k.close for k in kept):
            continue
        kept.append(decl)
    return kept


def _count_top_level_commas(params: str) -> int:
    if not params.strip():
        return 0
    depth = 0
    count = 1
    for ch in params:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            count += 1
    return count


def _hash_decl(signature: str, masked: str, open_pos: int, close_pos: int, name: str) -> str:
    """Hash a declaration's shape: signature plus body, minus names and layout.

    Names are blanked so that a rename keeps the same hash and the matcher can
    pair the two as ``moved``; the parameters stay, so a signature change is a
    modification rather than a no-op.
    """
    sig = re.sub(r"\s+", "", signature)
    body = re.sub(r"\s+", "", masked[open_pos + 1 : close_pos])
    return hashlib.sha1((sig + "|" + body).encode("utf-8")).hexdigest()


def _lines_above(source: str, pos: int, limit: int = 6) -> List[str]:
    """Stripped text of the lines just above ``pos``, nearest first."""
    line_start = source.rfind("\n", 0, pos) + 1
    lines: List[str] = []
    for _ in range(limit):
        if line_start <= 0:
            break
        prev = source.rfind("\n", 0, line_start - 1) + 1
        lines.append(source[prev:line_start].strip())
        line_start = prev
    return lines


def _decorators_before(source: str, pos: int) -> List[str]:
    found: List[str] = []
    for text in _lines_above(source, pos):
        if not text:
            continue
        if text.startswith("@"):
            found.insert(0, text)
            continue
        break
    return found


def _has_doc_before(source: str, pos: int) -> bool:
    for text in _lines_above(source, pos):
        if not text or text.startswith("@"):
            continue
        return text.endswith("*/")
    return False


def _count_code_lines(masked: str, start_line: int, end_line: int) -> int:
    total = 0
    for index, text in enumerate(masked.splitlines(), start=1):
        if index < start_line:
            continue
        if index > end_line:
            break
        if text.strip():
            total += 1
    return total


def _build_tree(
    decls: List[_Decl], masked: str, lines: List[str], line_of: List[int]
) -> List[Symbol]:
    ordered = sorted(decls, key=lambda d: (d.open, -d.close))
    stack: List[Tuple[_Decl, Symbol]] = []
    roots: List[Symbol] = []

    for decl in ordered:
        while stack and not (stack[-1][0].open < decl.open < stack[-1][0].close):
            stack.pop()
        parents = [sym for _, sym in stack]
        qualname = ".".join([sym.name for sym in parents] + [decl.name])
        kind = decl.kind
        if not decl.is_container:
            parent_kind = stack[-1][1].kind if stack else ""
            kind = "method" if parent_kind in _METHOD_CONTAINERS else "function"

        symbol = Symbol(
            kind=kind,
            name=decl.name,
            qualname=qualname,
            lineno=decl.lineno,
            end_lineno=decl.end_lineno,
            depth=len(stack),
            loc=_count_code_lines(masked, decl.lineno, decl.end_lineno),
            complexity=_complexity(masked, decl.open, decl.close),
            params=0 if decl.is_container else decl.params,
            decorators=decl.decorators,
            has_doc=decl.has_doc,
            body_hash=decl.body_hash,
        )
        if parents:
            parents[-1].children.append(symbol)
        else:
            roots.append(symbol)
        if decl.is_container:
            stack.append((decl, symbol))

    return roots


def _complexity(masked: str, open_pos: int, close_pos: int) -> int:
    return 1 + len(_COMPLEXITY_RE.findall(masked[open_pos:close_pos]))
