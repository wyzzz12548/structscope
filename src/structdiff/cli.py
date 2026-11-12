"""Command line interface for StructDiff."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Sequence

from .diff import diff_files
from .model import StructDiffError
from .render import render_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structdiff",
        description="Structural diff for Python: see what changed, not which characters.",
    )
    parser.add_argument("old", help="the original .py file")
    parser.add_argument("new", help="the updated .py file")
    parser.add_argument(
        "-o",
        "--output",
        help="report path (default: <new file>.structdiff.html)",
    )
    parser.add_argument("--old-label", default="", help="label for the left column")
    parser.add_argument("--new-label", default="", help="label for the right column")
    parser.add_argument("--title", default="", help="report title")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the summary as JSON instead of writing a report",
    )
    parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="open the report in the default browser",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="print nothing on success")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    _safe_stdout()
    args = build_parser().parse_args(argv)

    try:
        result = diff_files(
            args.old,
            args.new,
            old_label=args.old_label,
            new_label=args.new_label,
        )
    except StructDiffError as exc:
        print(f"structdiff: {exc}", file=sys.stderr)
        return 2

    summary = result.summary()

    if args.json:
        json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if args.output:
        output = Path(args.output)
    else:
        output = Path(args.new).with_suffix(".structdiff.html")

    try:
        output.write_text(render_html(result, title=args.title or None), encoding="utf-8")
    except OSError as exc:
        print(f"structdiff: cannot write {output}: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(_summary_line(summary))
        size_kb = max(1, output.stat().st_size // 1024) if output.exists() else 0
        print(f"wrote {output} ({size_kb} KB)")

    if args.open_browser:
        webbrowser.open(output.resolve().as_uri())

    return 0


def _summary_line(summary) -> str:
    parts = []
    for key in ("added", "removed", "modified", "moved"):
        if summary[key]:
            parts.append(f"{summary[key]} {key}")
    if summary["unchanged"]:
        parts.append(f"{summary['unchanged']} unchanged")
    parts.append(
        f"LOC {summary['old_loc']} -> {summary['new_loc']} ({summary['loc_delta']:+d})"
    )
    return "structdiff: " + ", ".join(parts)


def _safe_stdout() -> None:
    """Never crash a Windows console that cannot encode an arrow."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
