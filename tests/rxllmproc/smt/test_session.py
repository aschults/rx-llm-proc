"""Tests for Z3 Session."""

import unittest
import os
import shutil
from rxllmproc import smt
from rxllmproc.smt import session as smt_session


@unittest.skipUnless(smt.Z3_AVAILABLE, "z3-solver not installed")
class TestZ3Session(unittest.TestCase):
    """Test the Z3Session class."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = "test_z3_code"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init(self):
        """Test session initialization."""
        session = smt_session.Z3Session(base_dir=self.test_dir)
        self.assertIsNotNone(session.solver)
        self.assertEqual(session.metadata.copy(), {})

    def test_push_pop(self):
        """Test push and pop methods."""
        session = smt_session.Z3Session(base_dir=self.test_dir)
        session.push()
        session.pop()

    def test_metadata(self):
        """Test metadata management."""
        session = smt_session.Z3Session(base_dir=self.test_dir)
        session.add_metadata("fact1", "This is a fact")
        self.assertEqual(session.get_description("fact1"), "This is a fact")
        self.assertIsNone(session.get_description("nonexistent"))

    def test_export_load_state(self):
        """Test state serialization and rehydration."""
        import z3

        session = smt_session.Z3Session(base_dir=self.test_dir)
        x = z3.Int('x')
        session.solver.add(x > 10)
        session.add_metadata("h1", "x is greater than 10")

        state = session.export_state()
        self.assertIn("smt2", state)
        self.assertIn("metadata", state)
        self.assertEqual(state["metadata"]["h1"], "x is greater than 10")

        new_session = smt_session.Z3Session(base_dir=self.test_dir)
        new_session.load_state(state["smt2"], state["metadata"])
        self.assertEqual(
            new_session.get_description("h1"), "x is greater than 10"
        )
        self.assertEqual(str(new_session.solver.check()), "sat")

    def test_save_load_file(self):
        """Test file saving and loading."""
        session = smt_session.Z3Session(base_dir=self.test_dir)
        session.add_metadata("sort1", "Description of sort1")

        filename = "test_save.smt2"
        session.save_to_file(filename)

        # Verify both files created
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, filename)))
        self.assertTrue(
            os.path.exists(os.path.join(self.test_dir, filename + ".json"))
        )

        # Load into new session
        new_session = smt_session.Z3Session(base_dir=self.test_dir)
        data = new_session.load_from_file(filename)
        self.assertIn("smt2", data)
        self.assertEqual(data["metadata"]["sort1"], "Description of sort1")

    def test_path_traversal(self):
        """Test path traversal protection."""
        session = smt_session.Z3Session(base_dir=self.test_dir)
        with self.assertRaises(ValueError):
            session.save_to_file("../traversal.smt2")
        with self.assertRaises(ValueError):
            session.load_from_file("../traversal.smt2")


if __name__ == "__main__":
    unittest.main()
