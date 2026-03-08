"""Support to process Jinja in a defined environment."""

from . import html_processing, email_processing, ProcessingException
import logging
from typing import Any, Iterable, Callable

import jinja2
import markdownify  # type: ignore


class JinjaProcessingException(ProcessingException):
    """Exception during processing Jinja.

    May wrap an original Jinja Exception.
    """


class JinjaNoTemplateException(JinjaProcessingException):
    """Raised when template is not yet set.

    May wrap an original Jinja Exception.
    """


class JinjaProcessing:
    """Wrapper around Jinja to simplify processing."""

    def clean_html(self, msg: str) -> str:
        """Clean up the incoming HTML message."""
        return html_processing.HtmlCleaner().process(msg)

    def as_markdown(self, value: str) -> str:
        """Convert the HTML string value to markdown."""
        try:
            return markdownify.markdownify(value)  # type: ignore
        except Exception:
            logging.exception(
                'Exception during markdownify. Content: %s', value
            )
            raise

    def req(self, value: Any, message: str = '') -> Any:
        """Raise a JinjaProcessingException if value is undefined.

        Prevents successfully rendering unless all of the required values are
        defined.
        """
        if isinstance(value, jinja2.Undefined):
            error_msg = 'value is not set'
            if message:
                error_msg = f'value is not set: {message}'
            raise JinjaProcessingException(error_msg)
        return value

    @jinja2.pass_context
    def render_filter(
        self, context: jinja2.runtime.Context, template: str, **kwargs: Any
    ) -> str:
        """Filter the passed value by interpreting it as a Jinja template."""
        inner_template = self.env.from_string(template)

        return inner_template.render(context.parent, **kwargs)

    def __init__(self, required_vars: Iterable[str] | None = None):
        """Set up the instance.

        Args:
            required_vars: variables that need to be passed to render().
            template_str: Initial template string.
        """
        self.required_vars: set[str] = set(required_vars or [])

        self.env = jinja2.Environment()

        get_email_content = email_processing.get_email_content

        self.add_filter('req', self.req)
        self.add_filter('as_markdown', self.as_markdown)
        self.add_filter('clean_html', self.clean_html)
        self.add_filter('email_msg', get_email_content)
        self.add_filter('render', self.render_filter)

        # Keep the original string to detect change in the value.
        self.template_str = ''
        self.template: jinja2.Template | None = None

    def add_filter(self, name: str, func: Callable[..., str]):
        """Add a Jinja filter."""
        if name in self.env.filters:  # type: ignore
            raise JinjaProcessingException(
                f'filter named {repr(name)} already defined.'
            )
        self.env.filters[name] = func  # type: ignore

    def add_global(self, name: str, value: Any):
        """Add a Jinja global."""
        if name in self.env.globals:
            raise JinjaProcessingException(
                f'global named {repr(name)} already defined.'
            )
        self.env.globals[name] = value

    def set_template(self, new_template: str):
        """Set the Jinja template."""
        if self.template is None or self.template_str != new_template:
            self.template_str = new_template
            self.template = self.env.from_string(new_template)

    def render(self, **kwargs: Any):
        """Render the template with the args given."""
        if not self.template:
            raise JinjaNoTemplateException('No template set when rendering.')

        available = set(kwargs.keys())
        if not available.issuperset(self.required_vars):
            missing = self.required_vars - available
            raise JinjaProcessingException(f'Missing keys {missing}')
        logging.debug('Rendering template with args %s', repr(kwargs))
        return self.template.render(**kwargs)
