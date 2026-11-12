"""Render a :class:`DiffResult` into one self-contained HTML file."""

from __future__ import annotations

import difflib
import json
import re
from html import escape
from importlib.resources import files
from typing import Any, Dict, List, Optional, Sequence

from .diff import DiffResult
from .model import Pair, Status, Symbol
from . import layout as layout_mod

_TOKEN = re.compile(r"__(TITLE|STATS|SVG|JSON|CSS|JS)__")


def render_html(result: DiffResult, title: Optional[str] = None) -> str:
    """Return a complete, offline HTML document."""
    geom = layout_mod.compute(result)
    payload = _payload(result, geom)
    svg = _svg(result, geom)
    stats = _stats_html(result, geom)

    if title is None:
        title = f"{result.old.label} → {result.new.label}"

    template = _asset("viewer.html")
    mapping = {
        "TITLE": escape(title),
        "STATS": stats,
        "SVG": svg,
        "JSON": json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"),
        "CSS": _asset("viewer.css"),
        "JS": _asset("viewer.js"),
    }
    return _TOKEN.sub(lambda match: mapping[match.group(1)], template)


def write_report(
    result: DiffResult,
    path: str,
    title: Optional[str] = None,
) -> str:
    """Write the HTML report to ``path`` and return that path."""
    html = render_html(result, title=title)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    return path


def _asset(name: str) -> str:
    return (files("structdiff") / "templates" / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- payload


def _payload(result: DiffResult, geom: Dict[str, Any]) -> Dict[str, Any]:
    panels = {}
    for pair in result.pairs:
        panels[pair.id] = _panel(pair, result)

    return {
        "old": _file_meta(result.old),
        "new": _file_meta(result.new),
        "summary": result.summary(),
        "panels": panels,
        "row_h": layout_mod.ROW_H,
    }


def _file_meta(file) -> Dict[str, Any]:
    return {
        "label": file.label,
        "path": file.path,
        "loc": file.loc,
        "symbols": file.symbol_count,
    }


def _panel(pair: Pair, result: DiffResult) -> Dict[str, Any]:
    old, new = pair.old, pair.new
    symbol = pair.symbol

    metrics: List[str] = []
    if old and new:
        metrics.append(_metric("lines", old.loc, new.loc))
        metrics.append(_metric("complexity", old.complexity, new.complexity))
        if old.params != new.params:
            metrics.append(_metric("params", old.params, new.params))
        else:
            metrics.append(f"{new.params} params")
        if old.kind != new.kind:
            metrics.append(f"{old.kind} → {new.kind}")
    else:
        metrics.append(f"{symbol.loc} lines")
        metrics.append(f"complexity {symbol.complexity}")
        metrics.append(f"{symbol.params} params")

    note = ""
    if pair.status is Status.MOVED and old and new:
        note = f"renamed / moved: {old.qualname} → {new.qualname}"
    elif pair.status is Status.ADDED:
        note = "new in this version"
    elif pair.status is Status.REMOVED:
        note = "no longer exists in this version"

    return {
        "id": pair.id,
        "name": symbol.name,
        "qualname": symbol.qualname,
        "kind": symbol.kind,
        "status": pair.status.value,
        "metrics": metrics,
        "note": note,
        "rows": _rows(pair, result),
    }


def _metric(label: str, before: int, after: int) -> str:
    delta = after - before
    if delta == 0:
        return f"{label} {before}"
    return f"{label} {before} → {after} ({delta:+d})"


def _rows(pair: Pair, result: DiffResult) -> List[List[Any]]:
    """Rows of ``[old_lineno, old_text, new_lineno, new_text, tag]``."""
    old, new = pair.old, pair.new

    if old and new:
        old_lines = result.old.lines[old.lineno - 1 : old.end_lineno]
        new_lines = result.new.lines[new.lineno - 1 : new.end_lineno]
        return _aligned(old_lines, new_lines, old.lineno, new.lineno)

    if old:
        lines = result.old.lines[old.lineno - 1 : old.end_lineno]
        return [[old.lineno + i, text, None, None, "del"] for i, text in enumerate(lines)]

    assert new is not None
    lines = result.new.lines[new.lineno - 1 : new.end_lineno]
    return [[None, None, new.lineno + i, text, "ins"] for i, text in enumerate(lines)]


def _aligned(
    old_lines: Sequence[str],
    new_lines: Sequence[str],
    old_start: int,
    new_start: int,
) -> List[List[Any]]:
    matcher = difflib.SequenceMatcher(a=list(old_lines), b=list(new_lines), autojunk=False)
    rows: List[List[Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                rows.append(
                    [
                        old_start + i1 + offset,
                        old_lines[i1 + offset],
                        new_start + j1 + offset,
                        new_lines[j1 + offset],
                        "eq",
                    ]
                )
        elif tag == "delete":
            for index in range(i1, i2):
                rows.append([old_start + index, old_lines[index], None, None, "del"])
        elif tag == "insert":
            for index in range(j1, j2):
                rows.append([None, None, new_start + index, new_lines[index], "ins"])
        else:  # replace
            left = list(range(i1, i2))
            right = list(range(j1, j2))
            for offset in range(max(len(left), len(right))):
                li = left[offset] if offset < len(left) else None
                ri = right[offset] if offset < len(right) else None
                rows.append(
                    [
                        old_start + li if li is not None else None,
                        old_lines[li] if li is not None else None,
                        new_start + ri if ri is not None else None,
                        new_lines[ri] if ri is not None else None,
                        "rep",
                    ]
                )
    return rows


# -------------------------------------------------------------------- svg

def _svg(result: DiffResult, geom: Dict[str, Any]) -> str:
    width = geom["width"]
    height = geom["height"]
    parts: List[str] = [
        f'<svg id="canvas" xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="ui-sans-serif, system-ui, Segoe UI, sans-serif">'
    ]

    parts.append(_column_header(result.old, 0))
    parts.append(_column_header(result.new, geom["new_x"]))

    by_pair = {pair.id: pair for pair in result.pairs}
    for pair in result.pairs:
        box = geom["boxes"].get(pair.id, {})
        if "old" not in box or "new" not in box:
            continue
        left = box["old"]
        right = box["new"]
        x1 = left["x"] + left["w"]
        y1 = left["y"] + left["h"] / 2
        x2 = right["x"]
        y2 = right["y"] + right["h"] / 2
        dx = max(36.0, (x2 - x1) * 0.42)
        path = f"M{x1:.1f},{y1:.1f} C{x1 + dx:.1f},{y1:.1f} {x2 - dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
        state = pair.status.value
        parts.append(
            f'<path class="link st-{state}" data-pair="{pair.id}" '
            f'data-status="{state}" d="{path}"/>'
        )

    for node in geom["old_nodes"]:
        parts.append(_node(node, by_pair, geom["max_loc"]))
    for node in geom["new_nodes"]:
        parts.append(_node(node, by_pair, geom["max_loc"]))

    parts.append("</svg>")
    return "".join(parts)


def _column_header(file, x: int) -> str:
    return (
        f'<g class="colhead" transform="translate({x},0)">'
        f'<text class="col-title" x="0" y="26">{escape(file.label)}</text>'
        f'<text class="col-sub" x="0" y="45">{file.loc} LOC · {file.symbol_count} symbols</text>'
        f"</g>"
    )


def _node(node: Dict[str, Any], by_pair: Dict[str, Pair], max_loc: int) -> str:
    symbol: Symbol = node["sym"]
    pair = by_pair.get(symbol.pair_id or "")
    state = symbol.status.value

    if pair and pair.old and pair.new and pair.old.complexity != pair.new.complexity:
        badge = f"{pair.old.complexity}→{pair.new.complexity}"
    else:
        badge = str(symbol.complexity)

    bar = max(3.0, (symbol.loc / max_loc) ** 0.5 * (node["w"] - 6))

    return (
        f'<g class="node st-{state}" data-pair="{escape(symbol.pair_id or "")}" '
        f'data-status="{state}" transform="translate({node["x"]},{node["y"]})">'
        f"<title>{escape(_tooltip(symbol, pair))}</title>"
        f'<rect class="card" width="{node["w"]}" height="{node["h"]}" rx="6"/>'
        f'<rect class="accent" x="0" y="0" width="3" height="{node["h"]}" rx="1.5"/>'
        f'<rect class="bar" x="3" y="{node["h"] - 4}" width="{bar:.1f}" height="2" rx="1"/>'
        f'<text class="nm" x="11" y="15">{escape(_clip(symbol.name, 27))}</text>'
        f'<text class="cx" x="{node["w"] - 8}" y="15" text-anchor="end">{escape(badge)}</text>'
        f"</g>"
    )


def _tooltip(symbol: Symbol, pair: Optional[Pair]) -> str:
    text = f"{symbol.qualname} · {symbol.kind} · {symbol.loc} lines · complexity {symbol.complexity}"
    if pair and pair.old and pair.new:
        d_loc = pair.new.loc - pair.old.loc
        d_cx = pair.new.complexity - pair.old.complexity
        if d_loc or d_cx:
            text += f"  ({d_loc:+d} lines, {d_cx:+d} complexity)"
    return text


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ------------------------------------------------------------------- stats


def _stats_html(result: DiffResult, geom: Dict[str, Any]) -> str:
    summary = result.summary()
    chips: List[str] = []

    for key in ("added", "removed", "modified", "moved"):
        count = summary[key]
        if count:
            chips.append(f'<span class="chip st-{key}">{count} {key}</span>')
    if summary["unchanged"]:
        chips.append(f'<span class="chip st-unchanged">{summary["unchanged"]} unchanged</span>')

    chips.append(
        f'<span class="chip">LOC {summary["old_loc"]} → {summary["new_loc"]} '
        f'({summary["loc_delta"]:+d})</span>'
    )
    chips.append(
        f'<span class="chip">complexity {summary["old_complexity"]} → '
        f'{summary["new_complexity"]} ({summary["complexity_delta"]:+d})</span>'
    )
    return "".join(chips)
