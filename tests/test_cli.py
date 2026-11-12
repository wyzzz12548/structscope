import os
import shutil
import unittest
from pathlib import Path

from structscope.cli import main

TMP_ROOT = Path(__file__).resolve().parent / "_tmp"


class CliTest(unittest.TestCase):
    def setUp(self):
        self.root = TMP_ROOT / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.root, True)

        self.old = self.root / "old.py"
        self.new = self.root / "new.py"
        self.old.write_text("def f(x):\n    return x\n", encoding="utf-8")
        self.new.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")

    def test_writes_report(self):
        out = self.root / "report.html"
        code = main([str(self.old), str(self.new), "-o", str(out), "-q"])
        self.assertEqual(code, 0)
        self.assertTrue(out.exists())
        self.assertIn("<svg", out.read_text(encoding="utf-8"))

    def test_default_output_name(self):
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            code = main([str(self.old), str(self.new), "-q"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "new.structscope.html").exists())

    def test_json_mode(self):
        code = main([str(self.old), str(self.new), "--json"])
        self.assertEqual(code, 0)

    def test_syntax_error_exits_2(self):
        bad = self.root / "bad.py"
        bad.write_text("def f(:\n", encoding="utf-8")
        out = self.root / "report.html"
        code = main([str(bad), str(self.new), "-o", str(out), "-q"])
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
