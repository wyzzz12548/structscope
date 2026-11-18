"""StructScope — see what a code change did to the structure, in one picture."""

from __future__ import annotations

from .diff import DiffResult, diff_files, diff_sources
from .langs import LANGUAGES, detect_language, display_name, resolve_language
from .model import FileModel, Pair, Status, StructScopeError, Symbol
from .parser import parse_file, parse_source
from .render import render_html, write_report

__version__ = "0.2.0"

__all__ = [
    "DiffResult",
    "FileModel",
    "LANGUAGES",
    "Pair",
    "Status",
    "StructScopeError",
    "Symbol",
    "detect_language",
    "diff_files",
    "diff_sources",
    "display_name",
    "parse_file",
    "parse_source",
    "render_html",
    "resolve_language",
    "write_report",
    "__version__",
]
