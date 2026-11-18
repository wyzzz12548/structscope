"""Tests for language detection and dispatch."""

import os
import unittest

from structscope import langs
from structscope.diff import diff_files, diff_sources
from structscope.model import StructScopeError


class TestDetection(unittest.TestCase):
    def test_extensions_map_to_languages(self):
        cases = {
            "a.py": "python",
            "a.java": "java",
            "a.cpp": "cpp",
            "a.hpp": "cpp",
            "a.c": "c",
            "a.cs": "csharp",
            "a.js": "javascript",
            "a.ts": "typescript",
        }
        for path, expected in cases.items():
            self.assertEqual(langs.detect_language(path), expected, path)

    def test_unknown_extension_is_none(self):
        self.assertIsNone(langs.detect_language("README"))

    def test_explicit_language_wins(self):
        self.assertEqual(langs.resolve_language("a.java", "cpp"), "cpp")

    def test_auto_falls_back_to_python(self):
        self.assertEqual(langs.resolve_language("notes.txt", "auto"), "python")

    def test_unknown_language_raises(self):
        with self.assertRaises(StructScopeError):
            langs.resolve_language("a.java", "cobol")


class TestDispatch(unittest.TestCase):
    def test_python_still_goes_through_ast(self):
        result = diff_sources("def f():\n    return 1\n", "def f():\n    return 2\n")
        self.assertEqual(result.language, "python")
        self.assertEqual(result.summary()["modified"], 1)

    def test_java_strings_are_parsed_as_java(self):
        result = diff_sources(
            "class A {\n  int f() { return 1; }\n}\n",
            "class A {\n  int f() { return 2; }\n}\n",
            old_label="A.java",
            new_label="A.java",
        )
        self.assertEqual(result.language, "java")
        self.assertEqual(result.summary()["modified"], 2)

    def test_gbk_encoded_file_is_read(self):
        tmp = os.path.join("tests", "_tmp", self._testMethodName)
        os.makedirs(tmp, exist_ok=True)
        before = os.path.join(tmp, "Before.java")
        after = os.path.join(tmp, "After.java")
        source = 'class A {\n  // 中文注释\n  int f() { return 1; }\n}\n'
        with open(before, "w", encoding="gb18030") as fh:
            fh.write(source)
        with open(after, "w", encoding="gb18030") as fh:
            fh.write(source.replace("return 1", "return 2"))
        result = diff_files(before, after)
        self.assertEqual(result.language, "java")
        self.assertEqual(result.summary()["modified"], 2)


class TestDisplay(unittest.TestCase):
    def test_display_names(self):
        self.assertEqual(langs.display_name("cpp"), "C++")
        self.assertEqual(langs.display_name("csharp"), "C#")


if __name__ == "__main__":
    unittest.main()
