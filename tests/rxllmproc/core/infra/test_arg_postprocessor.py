# pyright: basic
"""Test ArgPostProcessor."""

import argparse
import dataclasses
from typing import Any

from pyfakefs import fake_filesystem_unittest

from rxllmproc.core.infra import arg_postprocessor


@dataclasses.dataclass
class ConfigObj:
    name: str = "default"
    value: int = 0


@dataclasses.dataclass
class ConfigWithMeta:
    file_content: str | None = dataclasses.field(
        default=None, metadata={'expand_file': True}
    )
    mapping: dict[str, Any] | None = dataclasses.field(
        default=None,
        metadata={
            'expand_dict': True,
            'expand_values': 'expand_args_typed',
        },
    )
    flag_mapped: str | None = dataclasses.field(
        default=None, metadata={'flag_name': 'cli_flag'}
    )


class TestArgPostProcessor(fake_filesystem_unittest.TestCase):
    """Test the ArgPostProcessor class."""

    def setUp(self):
        self.setUpPyfakefs()
        self.processor = arg_postprocessor.ArgPostProcessor(
            namespace=argparse.Namespace()
        )

    def test_expand_arg(self):
        """Test expanding arguments with @ prefix."""
        self.fs.create_file("test.txt", contents="content")
        self.assertEqual(self.processor.expand_arg("@test.txt"), "content")
        self.assertEqual(self.processor.expand_arg("value"), "value")

    def test_expand_args_typed(self):
        """Test expanding typed arguments."""
        self.fs.create_file("test.json", contents='{"a": 1}')
        self.fs.create_file("test.txt", contents="text content")
        self.fs.create_file("f.json", contents='["a","c"]')

        # Test explicit types
        self.assertEqual(
            self.processor.expand_args_typed("(json)@test.json"), {"a": 1}
        )
        self.assertEqual(
            self.processor.expand_args_typed("(txt)@test.txt"), "text content"
        )
        self.assertEqual(
            self.processor.expand_args_typed('(json){"b": 2}'), {"b": 2}
        )

        # Test implicit types from extension
        self.assertEqual(
            self.processor.expand_args_typed("()@test.json"), {"a": 1}
        )

        # Test escaping
        self.assertEqual(
            self.processor.expand_args_typed(r"\(json)@test.json"),
            "(json)@test.json",
        )
        self.assertEqual(
            self.processor.expand_args_typed(r"\@test.json"),
            "@test.json",
        )

        # Test value without type
        self.assertEqual(self.processor.expand_args_typed("value"), "value")

        # Test empty type
        self.assertEqual(
            self.processor.expand_args_typed('()@f.json'), ['a', 'c']
        )

        # Test custom converter
        self.processor.arg_converters['x'] = lambda s: f'_{s}_'
        self.assertEqual(
            self.processor.expand_args_typed('(x)@test.txt'), '_text content_'
        )
        self.assertEqual(
            self.processor.expand_args_typed(r'(x)\@test.txt'), '_@test.txt_'
        )

    def test_expand_args_typed_email(self):
        """Test expanding email arguments."""
        email_content = (
            "Subject: Test Subject\n"
            "From: sender@example.com\n"
            "\n"
            "Body content"
        )
        self.fs.create_file("test.eml", contents=email_content)

        # Test explicit type (email)
        msg = self.processor.expand_args_typed("(email)@test.eml")
        self.assertEqual(msg["Subject"], "Test Subject")
        self.assertEqual(msg.get_content().strip(), "Body content")

        # Test explicit type (eml)
        msg = self.processor.expand_args_typed("(eml)@test.eml")
        self.assertEqual(msg["From"], "sender@example.com")

        # Test implicit type from extension
        msg = self.processor.expand_args_typed("()@test.eml")
        self.assertEqual(msg["Subject"], "Test Subject")

    def test_expand_files_typed(self):
        """Test expanding a list of files with types."""
        self.fs.create_file("f1.json", contents='[1]')
        self.fs.create_file("f2.txt", contents='text')
        self.fs.create_file("f3.x", contents='custom')

        self.processor.arg_converters['x'] = lambda s: f'_{s}_'

        results = self.processor.expand_files_typed(
            ["f1.json", "f2.txt", "f3.x"]
        )
        self.assertEqual(results, [[1], "text", "_custom_"])

    def test_expand_args_named(self):
        """Test expanding named arguments."""
        args = ["key1=value1", "key2=value2"]
        result = self.processor.expand_args_named(args)
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})
        self.assertEqual(self.processor.expand_args_named([]), {})

        with self.assertRaisesRegex(
            arg_postprocessor.UsageException,
            'needs to have assignment.*invalid',
        ):
            self.processor.expand_args_named(["invalid"])

    def test_apply_args_simple(self):
        """Test applying simple arguments to an object."""
        target = ConfigObj()

        self.processor.namespace = argparse.Namespace(name="new_name", value=42)

        self.processor.apply_args(target)
        self.assertEqual(target.name, "new_name")
        self.assertEqual(target.value, 42)

    def test_apply_args_dataclass_metadata(self):
        """Test applying arguments with dataclass metadata processing."""
        self.fs.create_file("content.txt", contents="file content")

        target = ConfigWithMeta()

        self.processor = arg_postprocessor.ArgPostProcessor(
            argparse.Namespace(
                file_content="@content.txt",
                mapping=["key=(json)[1, 2]"],
                cli_flag="flag_value",
            )
        )
        self.processor.apply_args(target)

        self.assertEqual(target.file_content, "file content")
        self.assertEqual(target.mapping, {"key": [1, 2]})
        self.assertEqual(target.flag_mapped, "flag_value")

    def test_apply_args_multiple_targets(self):
        """Test applying arguments to multiple target objects."""
        t1 = ConfigObj()
        t2 = ConfigObj()

        self.processor = arg_postprocessor.ArgPostProcessor(
            argparse.Namespace(name="shared_name")
        )
        self.processor.apply_args(t1, t2)
        self.assertEqual(t1.name, "shared_name")
        self.assertEqual(t2.name, "shared_name")

    def test_apply_args_unknown_field(self):
        """Test that unknown fields raise an exception."""
        target = ConfigObj()

        self.processor = arg_postprocessor.ArgPostProcessor(
            argparse.Namespace(unknown="value")
        )
        with self.assertRaises(KeyError):
            self.processor.apply_args(target)
