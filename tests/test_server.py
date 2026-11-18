"""Tests for the local web server: the picker page and the diff endpoint."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from structscope import server

PY_BEFORE = "def report(rows):\n    return rows\n"
PY_AFTER = "def report(rows):\n    return sorted(rows)\n"


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.load(response)


class TestHandleDiff(unittest.TestCase):
    def test_python_diff_returns_a_report_url(self):
        status, body = server.handle_diff(
            {
                "old": PY_BEFORE,
                "new": PY_AFTER,
                "oldName": "a.py",
                "newName": "b.py",
                "lang": "auto",
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["modified"], 1)
        report_id = str(body["url"]).rsplit("/", 1)[-1]
        self.assertIn("<svg", server._REPORTS[report_id])

    def test_language_choice_is_used(self):
        status, body = server.handle_diff(
            {
                "old": "class A {\n  int f() { return 1; }\n}\n",
                "new": "class A {\n  int f() { return 2; }\n}\n",
                "oldName": "A.java",
                "newName": "A.java",
                "lang": "java",
            }
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["language"], "java")

    def test_empty_file_is_rejected(self):
        status, body = server.handle_diff({"old": "", "new": PY_AFTER})
        self.assertEqual(status, 400)
        self.assertIn("empty", str(body["error"]))

    def test_syntax_error_is_reported_not_raised(self):
        status, body = server.handle_diff({"old": "def f(:\n", "new": PY_AFTER})
        self.assertEqual(status, 400)
        self.assertIn("syntax error", str(body["error"]))

    def test_non_object_payload_is_rejected(self):
        status, _ = server.handle_diff(["nope"])
        self.assertEqual(status, 400)

    def test_unknown_language_is_rejected(self):
        status, body = server.handle_diff({"old": PY_BEFORE, "new": PY_AFTER, "lang": "cobol"})
        self.assertEqual(status, 400)
        self.assertIn("unknown language", str(body["error"]))


class TestHttp(unittest.TestCase):
    def setUp(self):
        self.httpd = server.create_server(port=0, tries=1)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_picker_page_lists_two_file_inputs_and_languages(self):
        with urllib.request.urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
        self.assertIn('id="file-old"', html)
        self.assertIn('id="file-new"', html)
        self.assertIn('<option value="java">Java</option>', html)
        self.assertNotIn("__LANGUAGES__", html)

    def test_post_diff_then_fetch_report(self):
        status, body = _post(
            self.base + "/diff",
            {"old": PY_BEFORE, "new": PY_AFTER, "oldName": "a.py", "newName": "b.py", "lang": "auto"},
        )
        self.assertEqual(status, 200)
        with urllib.request.urlopen(self.base + body["url"]) as response:
            html = response.read().decode("utf-8")
        self.assertIn("<svg", html)
        self.assertIn("b.py", html)

    def test_malformed_body_returns_400(self):
        request = urllib.request.Request(
            self.base + "/diff", data=b"not json", headers={"Content-Type": "application/json"}
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()

    def test_unknown_report_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + "/report/deadbeef")
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
