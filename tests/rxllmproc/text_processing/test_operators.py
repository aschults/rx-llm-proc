"""Test the template reactive operators."""

import unittest
from unittest import mock
import reactivex as rx

from rxllmproc.text_processing import operators as template_operators
from rxllmproc.core import environment


class TestTemplateOperators(unittest.TestCase):
    """Test the template reactive operators."""

    def setUp(self):
        self.creds_patcher = mock.patch(
            'rxllmproc.core.auth.CredentialsFactory.shared_instance'
        )
        self.creds_patcher.start()
        self.env = environment.Environment()
        self.env.__enter__()

    def tearDown(self):
        self.env.__exit__(None, None, None)
        self.creds_patcher.stop()

    def test_render_template_dict(self):
        """Test rendering with a dictionary input."""
        results: list[str] = []
        source = rx.of({"name": "World"})
        template = "Hello {{name}}"

        source.pipe(
            template_operators.TemplateBuilder(template).create()
        ).subscribe(results.append)

        self.assertEqual(results, ["Hello World"])

    def test_render_template_data(self):
        """Test rendering with a non-dictionary input."""
        results: list[str] = []
        source = rx.of("World")
        template = "Hello {{data}}"

        source.pipe(
            template_operators.TemplateBuilder(template).create()
        ).subscribe(results.append)

        self.assertEqual(results, ["Hello World"])

    def test_render_template_with_globals(self):
        """Test rendering with global variables."""
        results: list[str] = []
        source = rx.of("World")
        template = "{{greeting}} {{data}}"

        source.pipe(
            template_operators.TemplateBuilder(template)
            .add_global("greeting", "Hello")
            .create()
        ).subscribe(results.append)

        self.assertEqual(results, ["Hello World"])

    def test_render_template_with_filter(self):
        """Test rendering with a custom filter."""
        results: list[str] = []
        source = rx.of("world")
        template = "Hello {{data | upper_case}}"

        def _upper_case(s: str) -> str:
            return s.upper()

        source.pipe(
            template_operators.TemplateBuilder(template)
            .add_filter("upper_case", _upper_case)
            .create()
        ).subscribe(results.append)

        self.assertEqual(results, ["Hello WORLD"])
