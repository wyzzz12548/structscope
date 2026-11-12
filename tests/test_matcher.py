import unittest

from structdiff.diff import diff_sources
from structdiff.model import Status


class MatchTest(unittest.TestCase):
    def test_unchanged(self):
        result = diff_sources("def f(x):\n    return x\n", "def f(x):\n    return x\n")
        self.assertEqual(result.counts["unchanged"], 1)
        self.assertEqual(result.pairs[0].status, Status.UNCHANGED)

    def test_modified(self):
        result = diff_sources(
            "def f(x):\n    return x\n",
            "def f(x):\n    return x + 1\n",
        )
        self.assertEqual(result.counts["modified"], 1)
        self.assertEqual(result.pairs[0].old.loc, 2)
        self.assertEqual(result.pairs[0].new.loc, 2)

    def test_added_and_removed(self):
        result = diff_sources(
            "def a():\n    return 1\n\ndef b():\n    return 2\n",
            "def a():\n    return 1\n",
        )
        self.assertEqual(result.counts["removed"], 1)
        self.assertEqual(result.counts["added"], 0)
        removed = result.by_status(Status.REMOVED)[0]
        self.assertEqual(removed.name, "b")
        self.assertIsNone(removed.new)

    def test_rename_is_moved_not_added(self):
        result = diff_sources(
            "def alpha(x):\n    return x + 1\n",
            "def beta(x):\n    return x + 1\n",
        )
        self.assertEqual(result.counts["moved"], 1)
        self.assertEqual(result.counts["added"], 0)
        self.assertEqual(result.counts["removed"], 0)
        pair = result.pairs[0]
        self.assertEqual(pair.old.name, "alpha")
        self.assertEqual(pair.new.name, "beta")

    def test_every_symbol_gets_a_pair(self):
        result = diff_sources(
            "class A:\n    def m(self):\n        return 1\n",
            "class A:\n    def m(self):\n        return 1\n\n    def n(self):\n        return 2\n",
        )
        self.assertEqual(result.counts["added"], 1)
        self.assertEqual(result.counts["modified"], 1)  # the class body grew
        self.assertEqual(result.counts["unchanged"], 1)
        for symbol in result.old.walk():
            self.assertIsNotNone(symbol.pair_id)
        for symbol in result.new.walk():
            self.assertIsNotNone(symbol.pair_id)

    def test_summary_deltas(self):
        result = diff_sources(
            "def f(x):\n    if x:\n        return 1\n    return 0\n",
            "def f(x):\n    return 1\n",
        )
        summary = result.summary()
        self.assertEqual(summary["complexity_delta"], -1)
        self.assertEqual(summary["loc_delta"], -2)


if __name__ == "__main__":
    unittest.main()
