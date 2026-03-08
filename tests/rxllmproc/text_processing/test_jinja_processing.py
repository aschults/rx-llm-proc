"""Test Jinja rendering."""

import unittest
from rxllmproc.text_processing import jinja_processing


class TestJinjaProcessing(unittest.TestCase):
    """Test template rendering with Jinja."""

    def test_expand(self):
        """Test a simple template expansion."""
        processor = jinja_processing.JinjaProcessing()

        processor.set_template('_{{a | req}}_')
        result = processor.render(a='the_value')

        self.assertEqual('_the_value_', result)

    def test_expand_req_fails(self):
        """Test a simple template expansion."""
        processor = jinja_processing.JinjaProcessing()

        processor.set_template('_{{a | req}}_')
        self.assertRaisesRegex(
            jinja_processing.JinjaProcessingException,
            'value is not set',
            lambda: processor.render(),
        )

    def test_expand_req_fails_message(self):
        """Test a simple template expansion."""
        processor = jinja_processing.JinjaProcessing()

        processor.set_template('_{{a | req("the_msg")}}_')
        self.assertRaisesRegex(
            jinja_processing.JinjaProcessingException,
            'value is not set.*the_msg',
            lambda: processor.render(),
        )

    def test_expand_multi(self):
        """Test expaning multiple values, some required."""
        processor = jinja_processing.JinjaProcessing()

        processor.set_template('_{{a | req}}_{{b}}_')
        self.assertEqual('_the_value__', processor.render(a='the_value'))
        self.assertEqual(
            '_the_value_another_', processor.render(a='the_value', b='another')
        )

    def test_template_update(self):
        """Ensure that updating the template input re-renders."""
        processor = jinja_processing.JinjaProcessing()

        processor.set_template('_{{a | req}}_')
        self.assertEqual('_the_value_', processor.render(a='the_value'))

        processor.set_template('+_{{a | req}}_+')
        self.assertEqual('+_the_value2_+', processor.render(a='the_value2'))

    def test_render_filter(self):
        """Test the render filter."""
        processor = jinja_processing.JinjaProcessing()
        processor.set_template('{{ tpl | render }}')
        result = processor.render(tpl='Hello {{ name }}', name='World')
        self.assertEqual('Hello World', result)

    def test_render_filter_args(self):
        """Test the render filter with arguments."""
        processor = jinja_processing.JinjaProcessing()
        processor.set_template('{{ tpl | render(name="Universe") }}')
        result = processor.render(tpl='Hello {{ name }}')
        self.assertEqual('Hello Universe', result)

    def test_render_filter_override(self):
        """Test the render filter overriding arguments."""
        processor = jinja_processing.JinjaProcessing()
        processor.set_template('{{ tpl | render(name="Universe") }}')
        result = processor.render(tpl='Hello {{ name }}', name='World')
        self.assertEqual('Hello Universe', result)
