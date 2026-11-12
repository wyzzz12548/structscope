import json
import re
import unittest

from structdiff.diff import diff_sources
from structdiff.render import render_html

PAYLOAD = re.compile(
    r'<script id="payload" type="application/json">(.*?)</script>', re.S
)


def payload_of(html: str) -> dict:
    match = PAYLOAD.search(html)
    assert match is not None, "payload script tag missing"
    return json.loads(match.group(1))


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.html = render_html(
            diff_sources(
                "def load(path):\n    return open(path).read()\n\ndef gone():\n    return 1\n",
                "def load(path):\n    return open(path).read()\n\ndef gone():\n    return 2\n\ndef fresh():\n    return 3\n",
                old_label="before.py",
                new_label="after.py",
            )
        )

    def test_is_a_complete_document(self):
        self.assertTrue(self.html.lstrip().lower().startswith("<!doctype html>"))
        self.assertIn('id="canvas"', self.html)
        self.assertIn("</svg>", self.html)

    def test_payload_round_trips(self):
        data = payload_of(self.html)
        self.assertEqual(data["summary"]["added"], 1)
        self.assertEqual(data["summary"]["modified"], 1)
        self.assertEqual(data["summary"]["unchanged"], 1)
        self.assertEqual(data["old"]["label"], "before.py")

    def test_every_pair_has_a_panel(self):
        data = payload_of(self.html)
        for pair_id in data["panels"]:
            self.assertIn("rows", data["panels"][pair_id])

    def test_added_panel_shows_new_lines_only(self):
        data = payload_of(self.html)
        panel = next(p for p in data["panels"].values() if p["status"] == "added")
        self.assertTrue(panel["rows"])
        for row in panel["rows"]:
            self.assertIsNone(row[0])
            self.assertIsNotNone(row[2])

    def test_no_external_assets(self):
        self.assertNotIn("<script src", self.html)
        self.assertNotIn("<link rel=\"stylesheet\"", self.html)
        self.assertNotIn("cdn.", self.html)

    def test_labels_are_escaped(self):
        html = render_html(
            diff_sources("def f():\n    pass\n", "def f():\n    pass\n"),
            title="a < b & c",
        )
        self.assertIn("a &lt; b &amp; c", html)


if __name__ == "__main__":
    unittest.main()
