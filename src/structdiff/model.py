"""Data model: a parsed file, its symbols, and the diff between two files."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional


class StructDiffError(Exception):
    """Raised when a file cannot be read or parsed."""


class Status(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    UNCHANGED = "unchanged"


@dataclass
class Symbol:
    """One named unit of code: a function, method, class, or nested function."""

    kind: str  # "function" | "method" | "nested" | "class"
    name: str
    qualname: str
    lineno: int
    end_lineno: int
    depth: int
    loc: int  # non-blank, non-comment lines inside this symbol
    complexity: int  # McCabe-style cyclomatic complexity
    params: int = 0
    decorators: List[str] = field(default_factory=list)
    has_doc: bool = False
    body_hash: str = ""  # hash of the AST with line numbers stripped
    children: List["Symbol"] = field(default_factory=list)

    # Filled in by the matcher.
    status: Status = Status.UNCHANGED
    pair_id: Optional[str] = None

    @property
    def n_lines(self) -> int:
        """Physical line span, including blanks and comments."""
        return max(0, self.end_lineno - self.lineno + 1)

    @property
    def label(self) -> str:
        if self.kind == "class":
            return f"class {self.name}"
        return f"def {self.name}" if self.kind != "nested" else f"def {self.name}"


@dataclass
class FileModel:
    path: str
    label: str
    source: str
    lines: List[str]
    symbols: List[Symbol]
    loc: int = 0

    def walk(self) -> Iterator[Symbol]:
        """Yield every symbol, parents before children."""
        stack = list(reversed(self.symbols))
        while stack:
            sym = stack.pop()
            yield sym
            stack.extend(reversed(sym.children))

    @property
    def symbol_count(self) -> int:
        return sum(1 for _ in self.walk())


@dataclass
class Pair:
    """One row of the diff: a symbol from the old file, the new file, or both."""

    id: str
    old: Optional[Symbol]
    new: Optional[Symbol]
    status: Status

    @property
    def symbol(self) -> Symbol:
        sym = self.new or self.old
        assert sym is not None
        return sym

    @property
    def name(self) -> str:
        return self.symbol.name
