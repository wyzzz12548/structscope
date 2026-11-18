"""Which language is this file, and which parser reads it."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from . import cparse
from .model import FileModel, StructScopeError
from .parser import parse_source as _parse_python

#: language id -> (display name, file extensions, family)
_SPECS: Dict[str, Tuple[str, Tuple[str, ...], str]] = {
    "python": ("Python", (".py", ".pyw"), "python"),
    "java": ("Java", (".java",), "brace"),
    "cpp": ("C++", (".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".ipp", ".ino", ".h"), "brace"),
    "c": ("C", (".c",), "brace"),
    "csharp": ("C#", (".cs",), "brace"),
    "javascript": ("JavaScript", (".js", ".mjs", ".jsx"), "brace"),
    "typescript": ("TypeScript", (".ts", ".tsx"), "brace"),
}

#: language ids in menu order
LANGUAGES: List[str] = ["python", "java", "cpp", "c", "csharp", "javascript", "typescript"]

_EXT_TO_LANG: Dict[str, str] = {}
for _lang, (_display, _exts, _family) in _SPECS.items():
    for _ext in _exts:
        _EXT_TO_LANG.setdefault(_ext, _lang)


def display_name(language: str) -> str:
    return _SPECS.get(language, (language.title(), (), "brace"))[0]


def extensions(language: str) -> Tuple[str, ...]:
    return _SPECS.get(language, ("", (), "brace"))[1]


def detect_language(path: str) -> Optional[str]:
    """Guess a language from a file name, or ``None``."""
    return _EXT_TO_LANG.get(os.path.splitext(path)[1].lower())


def resolve_language(path: str, forced: Optional[str] = None) -> str:
    """Pick a language: an explicit choice wins, otherwise the extension does."""
    if forced and forced not in ("auto", ""):
        if forced not in _SPECS:
            raise StructScopeError(
                f"unknown language {forced!r}; choose one of: {', '.join(LANGUAGES)}"
            )
        return forced
    return detect_language(path) or "python"


def read_source(path: str, language: Optional[str] = None) -> str:
    """Read a source file, trying the encodings a student's editor might pick."""
    language = language or resolve_language(path)
    if language == "python":
        from .parser import read_source as _read_python

        return _read_python(path)

    raw = _read_bytes(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_bytes(path: str) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise StructScopeError(f"cannot read {path}: {exc}") from exc


def parse(
    language: str,
    source: str,
    path: str = "<source>",
    label: str = "",
) -> FileModel:
    """Parse ``source`` with the front end that matches ``language``."""
    if language == "python":
        return _parse_python(source, path=path, label=label)
    return cparse.parse_c_like(source, path=path, label=label, language=language)


def parse_file(path: str, label: str = "", language: Optional[str] = None) -> FileModel:
    language = resolve_language(path, language)
    return parse(language, read_source(path, language), path=path, label=label or path)
