"""High-level API: diff two files or two source strings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .matcher import match
from .model import FileModel, Pair, Status
from .parser import parse_file, parse_source


@dataclass
class DiffResult:
    old: FileModel
    new: FileModel
    pairs: List[Pair]

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
        }


def diff_sources(
    old_source: str,
    new_source: str,
    old_label: str = "old",
    new_label: str = "new",
) -> DiffResult:
    """Diff two strings of Python source."""
    old = parse_source(old_source, path=old_label, label=old_label)
    new = parse_source(new_source, path=new_label, label=new_label)
    return DiffResult(old=old, new=new, pairs=match(old.symbols, new.symbols))


def diff_files(
    old_path: str,
    new_path: str,
    old_label: str = "",
    new_label: str = "",
) -> DiffResult:
    """Diff two ``.py`` files on disk."""
    old = parse_file(old_path, label=old_label or old_path)
    new = parse_file(new_path, label=new_label or new_path)
    return DiffResult(old=old, new=new, pairs=match(old.symbols, new.symbols))
