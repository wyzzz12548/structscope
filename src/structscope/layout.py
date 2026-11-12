"""Geometry: turn a diff into rows of boxes for the two columns."""

from __future__ import annotations

from typing import Any, Dict, List

from .diff import DiffResult
from .model import FileModel

ROW_H = 27
NODE_H = 22
INDENT = 18
NODE_W = 264
GUTTER = 190
TOP = 76


def compute(result: DiffResult) -> Dict[str, Any]:
    old_nodes, old_right = _side(result.old, 0)
    new_x = old_right + GUTTER
    new_nodes, new_right = _side(result.new, new_x)

    boxes: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for side, nodes in (("old", old_nodes), ("new", new_nodes)):
        for node in nodes:
            pair_id = node["sym"].pair_id
            if pair_id:
                boxes.setdefault(pair_id, {})[side] = node

    rows = max(len(old_nodes), len(new_nodes), 1)
    max_loc = max(
        [node["sym"].loc for node in old_nodes + new_nodes] or [1]
    ) or 1

    return {
        "old_nodes": old_nodes,
        "new_nodes": new_nodes,
        "boxes": boxes,
        "new_x": new_x,
        "width": max(new_right, old_right) + 28,
        "height": TOP + rows * ROW_H + 28,
        "max_loc": max_loc,
    }


def _side(file: FileModel, x0: int) -> "tuple[List[Dict[str, Any]], int]":
    nodes: List[Dict[str, Any]] = []
    row = 0

    def walk(symbols):
        nonlocal row
        for symbol in symbols:
            nodes.append(
                {
                    "sym": symbol,
                    "x": x0 + symbol.depth * INDENT,
                    "y": TOP + row * ROW_H,
                    "w": NODE_W,
                    "h": NODE_H,
                }
            )
            row += 1
            walk(symbol.children)

    walk(file.symbols)
    right = max((node["x"] + node["w"] for node in nodes), default=x0 + NODE_W)
    return nodes, right
