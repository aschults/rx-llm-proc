# pyright: basic
"""Test Conversion CLI class."""

import io
import contextlib
import logging
import unittest
from unittest import mock
from pyfakefs import fake_filesystem_unittest

from rxllmproc.cli import conversion_cli


class TestConversionCli(fake_filesystem_unittest.TestCase):
    """Test the conversion CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and instance."""
        super().setUp()
        self.setUpPyfakefs()
        self.instance = conversion_cli.ConversionCli()

    def test_html_to_markdown_file_to_file(self):
        """Test HTML to Markdown conversion from file to file."""
        html_content = "<h1>Title</h1><p>Some text.</p>"
        self.fs.create_file("input.html", contents=html_content)

        self.instance.main(["input.html", "--output", "output.md"])

        self.assertTrue(self.fs.exists("output.md"))
        output_file = self.fs.get_object("output.md")
        self.assertEqual(output_file.contents, "# Title\n\nSome text.\n")

    @mock.patch("sys.stdin")
    @mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_html_to_markdown_stdin_to_stdout(
        self, mock_stdout: io.StringIO, mock_stdin: mock.Mock
    ):
        """Test HTML to Markdown conversion from stdin to stdout."""
        html_content = "<h2>Subtitle</h2><div>Another paragraph.</div>"
        mock_stdin.read.return_value = html_content

        self.instance.main(
            [
                "--from-mime-type",
                "text/html",
                "--to-mime-type",
                "text/markdown",
            ]
        )

        self.assertEqual(
            mock_stdout.getvalue(), "## Subtitle\n\nAnother paragraph.\n"
        )

    def test_mime_type_override(self):
        """Test overriding MIME types with flags."""
        html_content = "<h3>Mime Override</h3>"
        self.fs.create_file("test.data", contents=html_content)

        self.instance.main(
            [
                "test.data",
                "--output",
                "result.txt",
                "--from-mime-type",
                "text/html",
                "--to-mime-type",
                "text/markdown",
            ]
        )

        self.assertTrue(self.fs.exists("result.txt"))
        output_file = self.fs.get_object("result.txt")
        self.assertEqual(output_file.contents, "### Mime Override\n")

    @mock.patch("sys.exit")
    @mock.patch("sys.stdin")
    def test_missing_input_mime_fails(
        self, mock_stdin: mock.Mock, mock_exit: mock.Mock
    ):
        """Test that the CLI fails if input MIME type cannot be determined."""
        mock_stdin.read.return_value = "some content"
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            self.instance.main(["--to-mime-type", "text/markdown"])

        mock_exit.assert_called_with(2)
        self.assertIn(
            "Cannot determine input MIME type", stderr_output.getvalue()
        )

    @mock.patch("sys.exit")
    def test_missing_output_mime_fails(self, mock_exit: mock.Mock):
        """Test that the CLI fails if output MIME type cannot be determined."""
        self.fs.create_file("input.html", contents="<p>hello</p>")
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            self.instance.main(["input.html"])

        mock_exit.assert_called_with(2)
        self.assertIn(
            "Cannot determine output MIME type", stderr_output.getvalue()
        )

    @mock.patch("sys.exit")
    def test_unsupported_conversion_fails(self, mock_exit: mock.Mock):
        """Test that an unsupported conversion raises a UsageException."""
        self.fs.create_file("input.txt", contents="hello world")
        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            self.instance.main(["input.txt", "--output", "output.md"])

        mock_exit.assert_called_with(2)
        self.assertIn("is not supported", stderr_output.getvalue())

    def test_conversion_uses_sanitizer(self):
        """Test that the conversion process correctly sanitizes HTML."""
        html_with_script = (
            "<h1>Welcome</h1><script>alert('pwned')</script><p>Safe text.</p>"
        )
        self.fs.create_file("unsafe.html", contents=html_with_script)

        self.instance.main(["unsafe.html", "-o", "safe.md"])

        self.assertTrue(self.fs.exists("safe.md"))
        output_file = self.fs.get_object("safe.md")
        self.assertEqual(output_file.contents, "# Welcome\n\nSafe text.\n")

    def test_dry_run(self):
        """Test that dry_run prevents file writing."""
        html_content = "<h1>Title</h1><p>Some text.</p>"
        self.fs.create_file("input.html", contents=html_content)
        logging.basicConfig(level=logging.INFO)

        stderr_output = io.StringIO()
        with contextlib.redirect_stderr(stderr_output):
            self.instance.main(
                ["--dry_run", "input.html", "--output", "output.md"]
            )

        self.assertFalse(self.fs.exists("output.md"))
        self.assertIn("**DRY RUN**", stderr_output.getvalue())


if __name__ == "__main__":
    unittest.main()
