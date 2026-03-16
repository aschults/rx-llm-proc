"""Tests for Z3 Auditor."""

import unittest
from rxllmproc import smt
from rxllmproc.smt import session as smt_session
from rxllmproc.smt import compiler as smt_compiler
from rxllmproc.smt import auditor as smt_auditor


@unittest.skipUnless(smt.Z3_AVAILABLE, "z3-solver not installed")
class TestZ3Auditor(unittest.TestCase):
    """Test the Z3Auditor class."""

    def test_check_consistency(self):
        """Test consistency check."""
        session = smt_session.Z3Session()
        compiler = smt_compiler.Z3Compiler(session)
        auditor = smt_auditor.Z3Auditor(session)

        compiler.declare_variable("x", "Int")
        compiler.assert_fact("f1", "(> x 10)", "x > 10")
        self.assertEqual(auditor.check_consistency(), "SAT")

        compiler.assert_fact("f2", "(< x 5)", "x < 5")
        self.assertEqual(auditor.check_consistency(), "UNSAT")

    def test_get_audit_trail(self):
        """Test generating an audit trail for UNSAT states."""
        session = smt_session.Z3Session()
        compiler = smt_compiler.Z3Compiler(session)
        auditor = smt_auditor.Z3Auditor(session)

        compiler.declare_variable("x", "Int")
        compiler.assert_fact("f1", "(> x 10)", "x > 10")
        compiler.assert_fact("f2", "(< x 5)", "x < 5")

        report = auditor.get_audit_trail()
        self.assertEqual(report["status"], "UNSAT")
        self.assertEqual(len(report["conflict_report"]), 2)
        labels = [item["label"] for item in report["conflict_report"]]
        self.assertIn("f1", labels)
        self.assertIn("f2", labels)

    def test_get_solution(self):
        """Test computing and returning a solution."""
        session = smt_session.Z3Session()
        compiler = smt_compiler.Z3Compiler(session)
        auditor = smt_auditor.Z3Auditor(session)

        compiler.declare_variable("x", "Int")
        compiler.assert_fact("f1", "(> x 10)", "x > 10")
        compiler.assert_fact("f2", "(< x 20)", "x < 20")

        # x could be 11 or 12, so it's ambiguous
        result = auditor.get_solution()
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIn("model", result)
        self.assertIn("x", result["model"])

        # Now add constraint to make it unique
        compiler.assert_fact("f3", "(= x 15)", "x is 15")
        result = auditor.get_solution()
        self.assertEqual(result["status"], "SAT")
        self.assertEqual(result["model"]["x"], "15")


if __name__ == "__main__":
    unittest.main()
