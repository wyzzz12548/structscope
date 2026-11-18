"""Command line interface for StructScope."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import List, Optional, Sequence

from . import langs
from .diff import diff_files
from .model import StructScopeError
from .render import render_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structscope",
        description=(
            "Structural diff: see what changed in the shape of your code, "
            "not which characters moved.  Reads Python, Java, C++, C#, "
            "JavaScript and TypeScript."
        ),
        epilog=(
            "Want to pick the files in a browser instead?  Run: "
            "structscope serve"
        ),
    )
    parser.add_argument("old", help="the original source file")
    parser.add_argument("new", help="the updated source file")
    parser.add_argument(
        "-o",
        "--output",
        help="report path (default: <new file>.structscope.html)",
    )
    parser.add_argument("--old-label", default="", help="label for the left column")
    parser.add_argument("--new-label", default="", help="label for the right column")
    parser.add_argument("--title", default="", help="report title")
    parser.add_argument(
        "--lang",
        default="auto",
        choices=["auto"] + langs.LANGUAGES,
        help="source language (default: guess from the file extension)",
    )
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


def build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="structscope serve",
        description="Open a local page where you pick two files in the browser.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: localhost only)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    parser.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="do not open a browser window",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    _safe_stdout()
    arguments: List[str] = list(argv if argv is not None else sys.argv[1:])

    if arguments and arguments[0] == "serve":
        return _serve_main(arguments[1:])

    args = build_parser().parse_args(arguments)

    try:
        result = diff_files(
            args.old,
            args.new,
            old_label=args.old_label,
            new_label=args.new_label,
            lang=args.lang,
        )
    except StructScopeError as exc:
        print(f"structscope: {exc}", file=sys.stderr)
        return 2

    summary = result.summary()

    if args.json:
        json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if args.output:
        output = Path(args.output)
    else:
        output = Path(args.new).with_suffix(".structscope.html")

    try:
        output.write_text(render_html(result, title=args.title or None), encoding="utf-8")
    except OSError as exc:
        print(f"structscope: cannot write {output}: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(_summary_line(summary, result.language_name))
        size_kb = max(1, output.stat().st_size // 1024) if output.exists() else 0
        print(f"wrote {output} ({size_kb} KB)")

    if args.open_browser:
        webbrowser.open(output.resolve().as_uri())

    return 0


def _serve_main(argv: Sequence[str]) -> int:
    from .server import serve

    args = build_serve_parser().parse_args(list(argv))
    try:
        return serve(host=args.host, port=args.port, open_browser=args.open_browser)
    except StructScopeError as exc:
        print(f"structscope: {exc}", file=sys.stderr)
        return 2


def _summary_line(summary, language: str = "") -> str:
    parts = []
    for key in ("added", "removed", "modified", "moved"):
        if summary[key]:
            parts.append(f"{summary[key]} {key}")
    if summary["unchanged"]:
        parts.append(f"{summary['unchanged']} unchanged")
    parts.append(
        f"LOC {summary['old_loc']} -> {summary['new_loc']} ({summary['loc_delta']:+d})"
    )
    prefix = f"structscope[{language}]" if language and language != "Python" else "structscope"
    return prefix + ": " + ", ".join(parts)


def _safe_stdout() -> None:
    """Never crash a Windows console that cannot encode an arrow."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
