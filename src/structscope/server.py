"""A tiny local web server: pick two files in the browser, get a report.

It exists because a browser cannot read a file the user has not chosen, and
because the parsers live in Python.  Nothing leaves the machine: the server
binds to 127.0.0.1 and the page is served from this package.
"""

from __future__ import annotations

import json
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple

from . import langs
from .diff import diff_sources
from .model import StructScopeError
from .render import _asset, render_html

MAX_BODY = 8 * 1024 * 1024  # 8 MB of source per file
MAX_REPORTS = 24

_REPORTS: Dict[str, str] = {}
_REPORT_ORDER: List[str] = []
_LOCK = threading.Lock()


def _store(html: str) -> str:
    report_id = uuid.uuid4().hex
    with _LOCK:
        _REPORTS[report_id] = html
        _REPORT_ORDER.append(report_id)
        while len(_REPORT_ORDER) > MAX_REPORTS:
            _REPORTS.pop(_REPORT_ORDER.pop(0), None)
    return report_id


def index_html() -> str:
    options = "\n".join(
        f'<option value="{lang}">{langs.display_name(lang)}</option>'
        for lang in langs.LANGUAGES
    )
    return _asset("picker.html").replace("__LANGUAGES__", options)


def _error(message: str, status: int = 400) -> Tuple[int, Dict[str, str]]:
    return status, {"error": message}


def handle_diff(payload: object) -> Tuple[int, Dict[str, object]]:
    """Compare two sources posted as JSON.  Pure function of its input."""
    if not isinstance(payload, dict):
        return _error("expected a JSON object")

    old = payload.get("old")
    new = payload.get("new")
    if not isinstance(old, str) or not isinstance(new, str):
        return _error("both files must be sent as text")
    if not old.strip() or not new.strip():
        return _error("one of the files is empty")

    old_name = str(payload.get("oldName") or "before")
    new_name = str(payload.get("newName") or "after")
    lang = str(payload.get("lang") or "auto")

    try:
        result = diff_sources(old, new, old_label=old_name, new_label=new_name, lang=lang)
    except StructScopeError as exc:
        return _error(str(exc))

    html = render_html(result, title=f"{old_name} \u2192 {new_name}")
    report_id = _store(html)
    return 200, {
        "url": f"/report/{report_id}",
        "language": result.language,
        "summary": result.summary(),
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "StructScope"

    def log_message(self, *args) -> None:  # keep the console quiet
        return

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", index_html())
        elif path.startswith("/report/"):
            report = _REPORTS.get(path[len("/report/") :])
            if report is None:
                self._send(404, "text/plain; charset=utf-8", "report expired")
            else:
                self._send(200, "text/html; charset=utf-8", report)
        elif path == "/favicon.ico":
            self._send(204, "text/plain", "")
        else:
            self._send(404, "text/plain; charset=utf-8", "not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/diff":
            self._send(404, "text/plain; charset=utf-8", "not found")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            status, body = _error("file too large or missing body")
            self._send_json(status, body)
            return

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            status, body = _error("malformed request")
            self._send_json(status, body)
            return

        status, body = handle_diff(payload)
        self._send_json(status, body)

    def _send_json(self, status: int, body: Dict[str, object]) -> None:
        self._send(status, "application/json; charset=utf-8", json.dumps(body, ensure_ascii=False))

    def _send(self, status: int, content_type: str, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if data:
            self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8000, tries: int = 10) -> ThreadingHTTPServer:
    """Bind the first free port, starting at ``port``."""
    last_error: Optional[OSError] = None
    for candidate in range(port, port + tries):
        try:
            return ThreadingHTTPServer((host, candidate), _Handler)
        except OSError as exc:
            last_error = exc
    raise StructScopeError(f"cannot bind {host}:{port}-{port + tries - 1}: {last_error}")


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> int:
    httpd = create_server(host, port)
    url = f"http://{host}:{httpd.server_port}/"
    print(f"StructScope is running at {url}")
    print("Pick two files in the browser.  Press Ctrl+C here to stop.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0
