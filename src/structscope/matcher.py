"""Match symbols from the old file to symbols in the new file.

Three passes, cheapest and most reliable first:

1. exact qualified name (``Cls.method``),
2. identical AST body (catches renamed / moved code),
3. fuzzy qualified-name similarity within the same kind.

Whatever is left over is reported as added or removed.
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Sequence, Set

from .model import Pair, Status, Symbol

FUZZY_THRESHOLD = 0.75


def _flatten(symbols: Sequence[Symbol]) -> Iterator[Symbol]:
    for symbol in symbols:
        yield symbol
        yield from _flatten(symbol.children)


def match(old_symbols: Sequence[Symbol], new_symbols: Sequence[Symbol]) -> List[Pair]:
    """Return the list of pairs covering every symbol on both sides."""
    old_all = list(_flatten(old_symbols))
    new_all = list(_flatten(new_symbols))

    used_old: Set[int] = set()
    used_new: Set[int] = set()
    pairs: List[Pair] = []

    def add(old: Optional[Symbol], new: Optional[Symbol]) -> Pair:
        if old is None:
            status = Status.ADDED
        elif new is None:
            status = Status.REMOVED
        elif old.body_hash != new.body_hash:
            status = Status.MODIFIED
        elif old.qualname != new.qualname:
            status = Status.MOVED
        else:
            status = Status.UNCHANGED

        pair = Pair(id=f"p{len(pairs) + 1}", old=old, new=new, status=status)
        pairs.append(pair)

        for symbol in (old, new):
            if symbol is not None:
                symbol.status = status
                symbol.pair_id = pair.id
        if old is not None:
            used_old.add(id(old))
        if new is not None:
            used_new.add(id(new))
        return pair

    # Pass 1: same qualified name.
    by_qualname: Dict[str, List[Symbol]] = defaultdict(list)
    for symbol in new_all:
        by_qualname[symbol.qualname].append(symbol)

    for old in old_all:
        for new in by_qualname.get(old.qualname, []):
            if id(new) not in used_new:
                add(old, new)
                break

    # Pass 2: identical body, different name -> renamed / moved code.
    old_unmatched = [s for s in old_all if id(s) not in used_old]
    new_unmatched = [s for s in new_all if id(s) not in used_new]
    old_by_hash: Dict[str, List[Symbol]] = defaultdict(list)
    new_by_hash: Dict[str, List[Symbol]] = defaultdict(list)
    for symbol in old_unmatched:
        old_by_hash[symbol.body_hash].append(symbol)
    for symbol in new_unmatched:
        new_by_hash[symbol.body_hash].append(symbol)

    for body_hash, old_group in old_by_hash.items():
        new_group = new_by_hash.get(body_hash, [])
        if len(old_group) == 1 and len(new_group) == 1:
            add(old_group[0], new_group[0])

    # Pass 3: fuzzy name similarity within the same kind.
    old_unmatched = sorted(
        (s for s in old_all if id(s) not in used_old), key=lambda s: s.qualname
    )
    for old in old_unmatched:
        best: Optional[Symbol] = None
        best_score = 0.0
        for new in new_all:
            if id(new) in used_new or new.kind != old.kind:
                continue
            score = difflib.SequenceMatcher(
                None, old.qualname, new.qualname
            ).ratio()
            if score > best_score:
                best, best_score = new, score
        if best is not None and best_score >= FUZZY_THRESHOLD:
            add(old, best)

    # Leftovers.
    for old in old_all:
        if id(old) not in used_old:
            add(old, None)
    for new in new_all:
        if id(new) not in used_new:
            add(None, new)

    return pairs
