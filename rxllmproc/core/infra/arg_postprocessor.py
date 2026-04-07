"""Argparse post-processing module."""

import argparse
import dataclasses
import json
import logging
import os
from email import policy
from email import parser
from email import message

import re
from typing import Any, Callable, Iterable, List, cast


class UsageException(Exception):
    """Exception to be raised for usage issues with the CLI."""

    def __init__(self, usage_text: str, *args: object) -> None:
        """Create an instance.

        Args:
            usage_text: Text to show as part of the usage message.
        """
        super().__init__(usage_text, *args)
        self.usage_text = usage_text


def _mail_parser(s: str) -> message.Message:
    return parser.BytesParser(policy=policy.default).parsebytes(s.encode())


def _is_pydantic_dataclass(obj: Any) -> bool:
    """Check if an object is a Pydantic dataclass."""
    return hasattr(obj, "__pydantic_fields__")


def _get_fields(obj: Any) -> Iterable[Any]:
    """Get fields from a dataclass or Pydantic dataclass."""
    if dataclasses.is_dataclass(obj):
        if _is_pydantic_dataclass(obj):
            # For pydantic dataclasses, we can use __pydantic_fields__
            # Each value is a FieldInfo object which has a 'metadata' attribute in V2
            # But it's easier to use the standard dataclasses.fields if it works
            try:
                return dataclasses.fields(obj)
            except Exception:
                # Fallback for some environments/versions if needed
                pass
        return dataclasses.fields(obj)
    return []


class ArgPostProcessor:
    """Post-processes parsed arguments."""

    TYPE_PREFIX_RE = re.compile(
        r'''
                               ^(?P<is_escaped>\\)?
                               (?:\(
                                    \s*(?P<type>[\w+\-/]*)\s*
                               \))?
                               (?P<is_filename_escaped>\\)?
                               (?P<is_filename>@)?
                               (?P<stripped_arg>.*)$''',
        re.X,
    )

    NAME_PREFIX_RE = re.compile(r'^(?P<name>\w+)=(?P<val>.*)$')

    def __init__(
        self,
        namespace: argparse.Namespace | None = None,
        arg_converters: dict[str, Callable[[str], Any]] | None = None,
    ) -> None:
        """Initialize the ArgPostProcessor."""
        self.namespace = namespace or argparse.Namespace()
        self.arg_converters = arg_converters or {
            'json': json.loads,
            'txt': lambda s: s,
            'email': _mail_parser,
            'eml': _mail_parser,
        }

    def expand_arg(self, arg: str) -> str:
        """Expand an arg to file content if prefixed with @."""
        if arg.startswith('@'):
            with open(arg[1:], 'r', encoding='utf-8') as input_file:
                return input_file.read()
        return arg

    def expand_args_typed(self, arg: str) -> Any:
        """Expand args with types."""
        match = self.TYPE_PREFIX_RE.fullmatch(arg)

        if not match:
            raise Exception(f'Could not match arg {repr(arg)}')
        if match.group('is_escaped'):
            return arg[1:]
        content = match.group('stripped_arg')
        filename = None
        if match.group('is_filename'):
            if match.group('is_filename_escaped'):
                content = '@' + content[:]
            else:
                filename = content
                with open(content, 'r', encoding='utf-8') as input_file:
                    content = input_file.read()

        arg_type = match.group('type')
        if arg_type is None:
            return content

        if not arg_type:  # Empty string
            if not filename:
                raise UsageException(
                    f'Arg is not a filename but no type given: {repr(arg)}'
                )
            _, arg_type = os.path.splitext(filename)
            arg_type = arg_type[1:]

        if arg_type in self.arg_converters:
            content = self.arg_converters[arg_type](content)
            return content

        raise UsageException(f'No argument type {repr(arg_type)} is known.')

    def expand_files_typed(self, args: Iterable[str]) -> List[Any]:
        """Load a list of files, typed by extension."""
        result: List[Any] = []
        for arg in args:
            with open(arg, 'r', encoding='utf-8') as input_file:
                content = input_file.read()
            _, arg_type = os.path.splitext(arg)
            arg_type = arg_type[1:]

            if arg_type in self.arg_converters:
                content = self.arg_converters[arg_type](content)
            else:
                logging.warning(
                    'File %s has unknown type, loading as text.', repr(arg)
                )
            result.append(content)
        return result

    def expand_args_named(
        self,
        args: Iterable[str],
        expand_func: Callable[[str], Any] = (lambda s: s),
    ) -> dict[str, Any]:
        """Convert an arg list as assignments (key=value) into a dict."""
        result: dict[str, str] = {}
        for arg in args:
            match = self.NAME_PREFIX_RE.fullmatch(arg)
            if not match:
                raise UsageException(
                    f'Arg needs to have assignment form: {repr(arg)}'
                )
            result[match.group('name')] = expand_func(match.group('val'))
        return result

    def _get_dataclass_field_value(
        self, obj: Any, name: str, value: Any
    ) -> Any:
        """Get the value for a dataclass field, processing metadata if needed."""
        for field in _get_fields(obj):
            metadata = getattr(field, 'metadata', {})
            match_name = metadata.get('flag_name', field.name)
            if match_name != name:
                continue
            if isinstance(value, str) and metadata.get('expand_file'):
                return cast(Any, self.expand_arg(value))
            elif isinstance(value, list) and metadata.get('expand_dict'):
                func_name = metadata.get('expand_values')
                func: Callable[[str], Any] = lambda s: s
                if func_name == 'expand_args_typed':
                    func = self.expand_args_typed
                elif func_name == 'expand_arg':
                    func = self.expand_arg
                elif func_name is not None:
                    raise ValueError(f'Unknown expand func {repr(func_name)}')
                return self.expand_args_named(cast(list[str], value), func)
            break
        return cast(Any, value)

    def apply_args(self, *targets: Any) -> None:
        """Apply parsed arguments to target_instance and config objects."""
        unique_targets = {id(obj): obj for obj in targets}.values()

        for name, value in vars(self.namespace).items():
            updated = False
            for obj in unique_targets:
                target_name = name
                is_dc = dataclasses.is_dataclass(obj)
                if is_dc:
                    for field in _get_fields(obj):
                        metadata = getattr(field, 'metadata', {})
                        if metadata.get('flag_name') == name:
                            target_name = field.name
                            break
                if hasattr(obj, target_name):
                    final_value = value
                    if is_dc:
                        final_value = self._get_dataclass_field_value(
                            obj, name, value
                        )
                    setattr(obj, target_name, final_value)
                    updated = True
            if not updated:
                raise KeyError(f'Flag {repr(name)} was not consumed')
