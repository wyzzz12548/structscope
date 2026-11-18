"""Tests for the brace-language parser (Java / C++ / C# / JavaScript)."""

import unittest

from structscope import cparse
from structscope.diff import diff_sources

JAVA = '''package demo;

/* A shape. */
public class Shape {
    private double x;

    public Shape(double x) {
        this.x = x;
    }

    /** Area of the shape. */
    public double area() {
        if (x < 0) {
            return 0;
        }
        return x * x;
    }
}
'''

CPP = '''#include <vector>

namespace geometry {

class Mesh {
public:
    Mesh(int n) : n_(n) {}

    double volume() const {
        if (n_ < 0 || n_ > 10) { return 0.0; }
        for (int i = 0; i < n_; ++i) { total += i; }
        return total;
    }

private:
    int n_;
    double total = 0.0;
};

double area(const Mesh& m) {
    return m.volume() * 2;
}

}  // namespace geometry
'''


def find(model, qualname):
    for symbol in model.walk():
        if symbol.qualname == qualname:
            return symbol
    raise AssertionError(f"no symbol named {qualname}")


class TestJava(unittest.TestCase):
    def setUp(self):
        self.model = cparse.parse_c_like(JAVA, path="Shape.java", language="java")

    def test_one_top_level_class(self):
        self.assertEqual([s.name for s in self.model.symbols], ["Shape"])
        self.assertEqual(self.model.symbols[0].kind, "class")

    def test_methods_become_children(self):
        shape = self.model.symbols[0]
        self.assertEqual([c.name for c in shape.children], ["Shape", "area"])
        self.assertTrue(all(c.kind == "method" for c in shape.children))

    def test_line_spans_cover_the_body(self):
        area = find(self.model, "Shape.area")
        self.assertEqual(area.lineno, 12)
        self.assertEqual(area.end_lineno, 17)

    def test_complexity_counts_the_if(self):
        self.assertEqual(find(self.model, "Shape.area").complexity, 2)

    def test_constructor_records_its_parameter(self):
        self.assertEqual(find(self.model, "Shape.Shape").params, 1)

    def test_loc_ignores_comments_and_blank_lines(self):
        area = find(self.model, "Shape.area")
        self.assertEqual(area.n_lines, 6)
        self.assertEqual(area.loc, 6)

    def test_javadoc_is_detected(self):
        self.assertTrue(find(self.model, "Shape.area").has_doc)
        self.assertFalse(find(self.model, "Shape.Shape").has_doc)


class TestCpp(unittest.TestCase):
    def setUp(self):
        self.model = cparse.parse_c_like(CPP, path="mesh.cpp", language="cpp")

    def test_namespace_wraps_the_class(self):
        self.assertEqual([s.name for s in self.model.symbols], ["geometry"])
        names = [s.qualname for s in self.model.walk()]
        self.assertIn("geometry.Mesh", names)
        self.assertIn("geometry.Mesh.volume", names)

    def test_free_function_in_namespace_is_a_function(self):
        self.assertEqual(find(self.model, "geometry.area").kind, "function")

    def test_initialiser_list_is_not_mistaken_for_code(self):
        ctor = find(self.model, "geometry.Mesh.Mesh")
        self.assertEqual(ctor.end_lineno, ctor.lineno)


class TestMasking(unittest.TestCase):
    def test_braces_inside_strings_do_not_break_matching(self):
        source = 'class A {\n  void f() {\n    String s = "}{";\n  }\n}\n'
        model = cparse.parse_c_like(source, path="A.java", language="java")
        method = find(model, "A.f")
        self.assertEqual(method.end_lineno, 4)

    def test_comments_are_blanked_but_keep_line_numbers(self):
        source = "class A {\n  // brace { in a comment\n  void f() {}\n}\n"
        model = cparse.parse_c_like(source, path="A.java", language="java")
        self.assertEqual(find(model, "A.f").lineno, 3)


class TestStructuralDiffAcrossLanguages(unittest.TestCase):
    def test_java_method_change_is_modified(self):
        before = "class A {\n  int f(int a) { return a; }\n}\n"
        after = "class A {\n  int f(int a, int b) { return a; }\n}\n"
        result = diff_sources(before, after, old_label="A.java", new_label="A.java", lang="java")
        self.assertEqual(result.language, "java")
        self.assertEqual(result.summary()["modified"], 2)  # the method and its class

    def test_renamed_function_is_reported_as_moved(self):
        before = "class A {\n  int alpha(int a) { return a * 2; }\n}\n"
        after = "class A {\n  int beta(int a) { return a * 2; }\n}\n"
        result = diff_sources(before, after, old_label="A.java", new_label="A.java", lang="java")
        statuses = {pair.status.value for pair in result.pairs}
        self.assertIn("moved", statuses)


if __name__ == "__main__":
    unittest.main()
