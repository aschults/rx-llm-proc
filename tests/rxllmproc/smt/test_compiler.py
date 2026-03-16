"""Tests for Z3 Compiler."""

import unittest
from rxllmproc import smt
from rxllmproc.smt import compiler as smt_compiler


@unittest.skipUnless(smt.Z3_AVAILABLE, "z3-solver not installed")
class TestZ3Compiler(unittest.TestCase):
    """Test the Z3Compiler class."""

    def test_init_session(self):
        """Test initializing a session with logic."""
        compiler = smt_compiler.Z3Compiler()
        result = compiler.init_session("QF_LIA")
        self.assertIn("QF_LIA", result)

    def test_declare_variable(self):
        """Test variable declaration."""
        compiler = smt_compiler.Z3Compiler()
        self.assertIn(
            "Int",
            compiler.declare_variable("x", "Int", description="An integer x"),
        )
        self.assertIn(
            "Real",
            compiler.declare_variable("y", "Real", description="A real y"),
        )
        self.assertIn(
            "Bool",
            compiler.declare_variable("z", "Bool", description="A boolean z"),
        )
        self.assertIn("already declared", compiler.declare_variable("x", "Int"))
        self.assertIn(
            "Unsupported type", compiler.declare_variable("w", "String")
        )

        # Verify descriptions
        self.assertEqual(compiler.session.get_description("x"), "An integer x")
        self.assertEqual(compiler.session.get_description("y"), "A real y")
        self.assertEqual(compiler.session.get_description("z"), "A boolean z")

    def test_declare_sort(self):
        """Test sort declaration."""
        compiler = smt_compiler.Z3Compiler()
        result = compiler.declare_sort("MySort", description="A custom sort")
        self.assertIn("Declared sort: MySort", result)
        self.assertEqual(
            compiler.session.get_description("MySort"), "A custom sort"
        )

        # Declare variable with custom sort
        result = compiler.declare_variable(
            "s", "MySort", description="Variable of MySort"
        )
        self.assertIn("MySort", result)
        self.assertEqual(
            compiler.session.get_description("s"), "Variable of MySort"
        )

    def test_declare_function(self):
        """Test function declaration."""
        compiler = smt_compiler.Z3Compiler()
        result = compiler.declare_function(
            "f", ["Int", "Int"], "Int", description="A binary function"
        )
        self.assertIn("Declared function: f", result)
        self.assertEqual(
            compiler.session.get_description("f"), "A binary function"
        )

    def test_assert_fact(self):
        """Test asserting a fact."""
        compiler = smt_compiler.Z3Compiler()
        compiler.declare_variable("x", "Int")
        result = compiler.assert_fact(
            "fact1", "(> x 10)", "x is greater than 10"
        )
        self.assertIn("Asserted fact: fact1", result)
        self.assertEqual(
            compiler.session.get_description("fact1"), "x is greater than 10"
        )
        self.assertEqual(str(compiler.session.solver.check()), "sat")

    def test_assert_fact_invalid_smt2(self):
        """Test error handling for invalid SMT2."""
        compiler = smt_compiler.Z3Compiler()
        # Missing parenthesis or unknown variable
        result = compiler.assert_fact(
            "err1", "(> unknown_var 10)", "test error"
        )
        self.assertIn("Error in SMT2 syntax", result)
        self.assertIn("unknown constant unknown_var", result)


if __name__ == "__main__":
    unittest.main()
