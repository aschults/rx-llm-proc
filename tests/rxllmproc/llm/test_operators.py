"""Test the LLM reactive operators."""

import unittest
import dataclasses
from unittest import mock
import reactivex as rx
from typing import Any

from rxllmproc.llm import operators as llm_operators
from rxllmproc.text_processing import operators as template_operators
from rxllmproc.core import environment
from rxllmproc.llm import commons as llm_commons


@dataclasses.dataclass
class SampleObj:
    """Sample dataclass for testing."""

    response: str


class TestLlmOperators(unittest.TestCase):
    """Test the LLM reactive operators."""

    def setUp(self):
        self.llm_mock = mock.Mock(spec=llm_commons.LlmBase)
        self.llm_mock.query.side_effect = lambda p: f"Response to: {p}"  # type: ignore
        self.llm_mock.query_json.side_effect = lambda p: {"response": p}  # type: ignore
        self.llm_mock.query_json_object.side_effect = lambda t, p: t(response=p)  # type: ignore

        patcher = mock.patch(
            'rxllmproc.llm.commons.LlmModelFactory.shared_instance'
        )
        self.factory_mock = patcher.start().return_value
        self.factory_mock.create.return_value = self.llm_mock
        self.addCleanup(patcher.stop)

        self.creds_patcher = mock.patch(
            'rxllmproc.core.auth.CredentialsFactory.shared_instance'
        )
        self.creds_patcher.start()
        self.addCleanup(self.creds_patcher.stop)

        self.env = environment.Environment()
        self.env.__enter__()
        self.addCleanup(lambda: self.env.__exit__(None, None, None))

    def test_generate_text_simple(self):
        """Test simple generation without template."""
        results: list[str] = []
        source = rx.of("Hello")

        source.pipe(llm_operators.generate_text()).subscribe(results.append)

        self.assertEqual(results, ["Response to: Hello"])
        self.llm_mock.query.assert_called_with("Hello")

    def test_generate_text_with_kwargs(self):
        """Test generation passing kwargs to factory."""
        results: list[str] = []
        source = rx.of("Hello")

        source.pipe(
            llm_operators.generate_text(model="my-model", api_key='testkey')
        ).subscribe(results.append)

        self.factory_mock.create.assert_called_with(
            "my-model", api_key='testkey', cache_instance=mock.ANY, functions=[]
        )
        self.assertEqual(results, ["Response to: Hello"])

    def test_generate_text_template_dict(self):
        """Test generation with template and dict input."""
        results: list[str] = []
        source = rx.of({"name": "World"})
        template = "Hello {{name}}"

        source.pipe(
            template_operators.TemplateBuilder(template).create(),
            llm_operators.generate_text(),
        ).subscribe(results.append)

        self.assertEqual(results, ["Response to: Hello World"])
        self.llm_mock.query.assert_called_with("Hello World")

    def test_generate_json(self):
        """Test JSON generation."""
        results: list[Any] = []
        source = rx.of("Hello")

        source.pipe(llm_operators.generate_json()).subscribe(results.append)

        self.assertEqual(results, [{"response": "Hello"}])
        self.llm_mock.query_json.assert_called_with("Hello")

    def test_generate_object(self):
        """Test object generation."""
        results: list[SampleObj] = []
        source = rx.of("Hello")

        source.pipe(llm_operators.generate_object(SampleObj)).subscribe(
            results.append
        )

        self.assertEqual(results, [SampleObj(response="Hello")])
        self.llm_mock.query_json_object.assert_called_with(SampleObj, "Hello")

    def test_generate_text_template_data(self):
        """Test generation with template and non-dict input."""
        results: list[str] = []
        source = rx.of("World")
        template = "Hello {{data}}"

        source.pipe(
            template_operators.TemplateBuilder(template).create(),
            llm_operators.generate_text(),
        ).subscribe(results.append)

        self.assertEqual(results, ["Response to: Hello World"])
        self.llm_mock.query.assert_called_with("Hello World")
