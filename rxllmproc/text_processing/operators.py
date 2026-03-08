"""Reactive operators for template processing."""

from typing import Callable, Any, Dict
import reactivex as rx
from reactivex import operators as ops
from reactivex import Observable
from rxllmproc.text_processing import jinja_processing
from rxllmproc.core import environment


class TemplateBuilder:
    """Builder for template operators."""

    def __init__(self, template: str):
        """Create a builder instance."""
        self._template = template
        self._globals: Dict[str, Any] = {}
        self._filters: Dict[str, Callable[..., Any]] = {}

    def add_globals(self, **kwargs: Any) -> "TemplateBuilder":
        """Add multiple global variables to the template context."""
        self._globals.update(kwargs)
        return self

    def add_global(self, name: str, value: Any) -> "TemplateBuilder":
        """Add a global variable to the template context."""
        self._globals[name] = value
        return self

    def add_filter(
        self, name: str, func: Callable[..., Any]
    ) -> "TemplateBuilder":
        """Add a custom filter to the template engine."""
        self._filters[name] = func
        return self

    def create(self) -> Callable[[Observable[Any]], Observable[str]]:
        """Create the operator."""
        processor = jinja_processing.JinjaProcessing()

        for name, value in environment.shared().template_globals.items():
            processor.add_global(name, value)
        for name, func in environment.shared().template_filters.items():
            processor.add_filter(name, func)

        for name, func in self._filters.items():
            processor.add_filter(name, func)
        for name, value in self._globals.items():
            processor.add_global(name, value)

        processor.set_template(self._template)

        def _render_template(source: Observable[Any]) -> Observable[str]:
            def _process(item: Any) -> Observable[str]:
                try:
                    if isinstance(item, dict):
                        return rx.just(processor.render(**item))
                    return rx.just(processor.render(data=item))
                except Exception as e:
                    return rx.throw(e)

            return source.pipe(ops.flat_map(_process))

        return _render_template
