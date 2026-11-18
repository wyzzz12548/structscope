"""High-level API: diff two files or two source strings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import langs
from .matcher import match
from .model import FileModel, Pair, Status


@dataclass
class DiffResult:
    old: FileModel
    new: FileModel
    pairs: List[Pair]
    language: str = "python"

    def by_status(self, status: Status) -> List[Pair]:
        return [pair for pair in self.pairs if pair.status is status]

    @property
    def counts(self) -> Dict[str, int]:
        counts = {status.value: 0 for status in Status}
        for pair in self.pairs:
            counts[pair.status.value] += 1
        return counts

    @property
    def changed(self) -> List[Pair]:
        return [pair for pair in self.pairs if pair.status is not Status.UNCHANGED]

    @property
    def language_name(self) -> str:
        return langs.display_name(self.language)

    def summary(self) -> Dict[str, int]:
        old_complexity = sum(s.complexity for s in self.old.walk())
        new_complexity = sum(s.complexity for s in self.new.walk())
        counts = self.counts
        return {
            "added": counts["added"],
            "removed": counts["removed"],
            "modified": counts["modified"],
            "moved": counts["moved"],
            "unchanged": counts["unchanged"],
            "old_loc": self.old.loc,
            "new_loc": self.new.loc,
            "loc_delta": self.new.loc - self.old.loc,
            "old_complexity": old_complexity,
            "new_complexity": new_complexity,
            "complexity_delta": new_complexity - old_complexity,
            "old_symbols": self.old.symbol_count,
            "new_symbols": self.new.symbol_count,
            "language": self.language,
        }


def diff_sources(
    old_source: str,
    new_source: str,
    old_label: str = "old",
    new_label: str = "new",
    lang: str = "auto",
) -> DiffResult:
    """Diff two strings of source code."""
    language = langs.resolve_language(old_label, lang)
    old = langs.parse(language, old_source, path=old_label, label=old_label)
    new = langs.parse(language, new_source, path=new_label, label=new_label)
    return DiffResult(old=old, new=new, pairs=match(old.symbols, new.symbols), language=language)


def diff_files(
    old_path: str,
    new_path: str,
    old_label: str = "",
    new_label: str = "",
    lang: str = "auto",
) -> DiffResult:
    """Diff two source files on disk."""
    language = langs.resolve_language(old_path, lang)
    old = langs.parse_file(old_path, label=old_label or old_path, language=language)
    new = langs.parse_file(new_path, label=new_label or new_path, language=language)
    return DiffResult(old=old, new=new, pairs=match(old.symbols, new.symbols), language=language)
