"""Reactive operators for LLMs."""

from typing import Callable, Any, TypeVar
import reactivex as rx
from reactivex import operators as ops
from rxllmproc.core import environment

_T = TypeVar("_T")


def generate_text(
    model: str | None = None,
    **kwargs: Any,
) -> Callable[[rx.Observable[str]], rx.Observable[str]]:
    """Generate text from an LLM based on the input.

    Args:
        model: The name of the LLM model to use. If None, uses default.
        **kwargs: Additional arguments for the model factory.

    Returns:
        An operator function.
    """
    llm = environment.shared().create_model(model, **kwargs)

    def _generate_text(source: rx.Observable[str]) -> rx.Observable[str]:
        def _process(item: str) -> rx.Observable[str]:
            try:
                return rx.just(llm.query(item))
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_process))

    return _generate_text


def generate_json(
    model: str | None = None,
    **kwargs: Any,
) -> Callable[[rx.Observable[str]], rx.Observable[Any]]:
    """Generate JSON from an LLM based on the input.

    Args:
        model: The name of the LLM model to use. If None, uses default.
        **kwargs: Additional arguments for the model factory.

    Returns:
        An operator function.
    """
    llm = environment.shared().create_model(model, **kwargs)

    def _generate_json(source: rx.Observable[str]) -> rx.Observable[Any]:
        def _process(item: str) -> rx.Observable[Any]:
            try:
                return rx.just(llm.query_json(str(item)))
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_process))

    return _generate_json


def generate_object(
    result_type: type[_T],
    model: str | None = None,
    **kwargs: Any,
) -> Callable[[rx.Observable[str]], rx.Observable[_T]]:
    """Generate a structured object from an LLM based on the input.

    Args:
        result_type: The type (dataclass) to generate.
        model: The name of the LLM model to use. If None, uses default.
        **kwargs: Additional arguments for the model factory.

    Returns:
        An operator function.
    """
    llm = environment.shared().create_model(model, **kwargs)

    def _generate_object(source: rx.Observable[str]) -> rx.Observable[_T]:
        def _process(item: Any) -> rx.Observable[_T]:
            try:
                return rx.just(llm.query_json_object(result_type, str(item)))
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_process))

    return _generate_object
