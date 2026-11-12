"""StructScope — see what a code change did to the structure, in one picture."""

from __future__ import annotations

from .diff import DiffResult, diff_files, diff_sources
from .model import FileModel, Pair, Status, StructScopeError, Symbol
from .parser import parse_file, parse_source
from .render import render_html, write_report

__version__ = "0.1.0"

__all__ = [
    "DiffResult",
    "FileModel",
    "Pair",
    "Status",
    "StructScopeError",
    "Symbol",
    "diff_files",
    "diff_sources",
    "parse_file",
    "parse_source",
    "render_html",
    "write_report",
    "__version__",
]
