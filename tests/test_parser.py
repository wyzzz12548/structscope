import unittest

from structdiff.model import StructDiffError
from structdiff.parser import parse_source

SOURCE = '''
class Store:
    """A tiny store."""

    def add(self, item, count=1):
        if count < 1:
            raise ValueError("count")
        for _ in range(count):
            self.items.append(item)


def top(a, b):
    return a if a > b else b
'''


class ParseSourceTest(unittest.TestCase):
    def setUp(self):
        self.model = parse_source(SOURCE, path="sample.py")

    def test_top_level_symbols(self):
        self.assertEqual([s.name for s in self.model.symbols], ["Store", "top"])

    def test_method_depth_and_qualname(self):
        store = self.model.symbols[0]
        self.assertEqual(store.kind, "class")
        self.assertEqual(store.depth, 0)

        method = store.children[0]
        self.assertEqual(method.kind, "method")
        self.assertEqual(method.qualname, "Store.add")
        self.assertEqual(method.depth, 1)

    def test_param_count(self):
        method = self.model.symbols[0].children[0]
        self.assertEqual(method.params, 3)  # self, item, count

    def test_complexity(self):
        method = self.model.symbols[0].children[0]
        self.assertEqual(method.complexity, 3)  # base 1 + if + for

        top = self.model.symbols[1]
        self.assertEqual(top.complexity, 2)  # base 1 + ternary

    def test_loc_ignores_blanks(self):
        top = self.model.symbols[1]
        self.assertEqual(top.loc, 2)  # def line + return line

    def test_body_hash_is_stable_across_whitespace(self):
        a = parse_source("def f(x):\n    return x + 1\n")
        b = parse_source("def f(x):\n\n    return x + 1  # note\n")
        self.assertEqual(a.symbols[0].body_hash, b.symbols[0].body_hash)

    def test_body_hash_changes_with_logic(self):
        a = parse_source("def f(x):\n    return x + 1\n")
        b = parse_source("def f(x):\n    return x + 2\n")
        self.assertNotEqual(a.symbols[0].body_hash, b.symbols[0].body_hash)

    def test_empty_file(self):
        model = parse_source("")
        self.assertEqual(model.symbols, [])
        self.assertEqual(model.loc, 0)


class ParseErrorTest(unittest.TestCase):
    def test_syntax_error_has_location(self):
        with self.assertRaises(StructDiffError) as ctx:
            parse_source("def f(:\n    pass\n", path="broken.py")
        self.assertIn("broken.py", str(ctx.exception))

    def test_syntax_error_does_not_leak_python_traceback(self):
        with self.assertRaises(StructDiffError):
            parse_source("class", path="broken.py")


if __name__ == "__main__":
    unittest.main()
