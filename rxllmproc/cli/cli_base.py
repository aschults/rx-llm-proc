"""Common base for all CLI."""

import logging
from typing import (
    List,
    Optional,
    Iterable,
    Callable,
    Any,
    Tuple,
    TypeVar,
)
import traceback
import sys
import os
import argparse
import datetime

from rxllmproc.core import auth
from rxllmproc.plugins import loader
from rxllmproc.core.infra import cache, containers
from rxllmproc.core.infra import arg_postprocessor

_T = TypeVar('_T')


def require_arg(arg: _T | None, name: str) -> _T:
    """Check that an argument is set and raise UsageException if not."""
    if arg is None:
        raise UsageException(f'{name} is required')
    return arg


UsageException = arg_postprocessor.UsageException


class CliBase:
    """Base class for all command line tools."""

    def _add_args(self):
        self.arg_parser.add_argument(
            '--verbose',
            '-v',
            action='count',
            help='Increase logging to verbose.',
            default=0,
        )
        self.arg_parser.add_argument(
            '--dry_run',
            action='store_true',
            help='Execute but don\'t change anything.',
        )
        self.arg_parser.add_argument(
            '--cache',
            help='Path to a cache file for LLM responses. Can also be set via RX_LLM_PROC_CACHE env var.',
        )
        self.arg_parser.add_argument(
            '--max_cache_age',
            default=30,
            type=int,
            help='Maximum age of cache entries in days since last accessed.',
        )

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        config_objects: List[Any] | None = None,
    ) -> None:
        """Create an instance, allowing for mocks (testing)."""
        self.arg_parser = argparse.ArgumentParser(
            epilog=(
                'Expects either client_secret.json and credentials.json in the '
                'current directory, or environment variables '
                'RX_LLM_PROC_GOOGLE_CLIENT_SECRET_FILE and '
                'RX_LLM_PROC_GOOGLE_CREDENTIALS_FILE pointing to OAuth Client '
                'Secret and current OAuth credential files in JSON. '
                'Will create or update the creadentials file after authentication.'
            )
        )
        self._add_args()

        self.plugins = loader.PluginRegistry(
            cred_store=creds,
            argparse_instance=self.arg_parser,
        )
        self.plugins.load_plugins()

        self.verbose = 0
        self.dry_run = False
        self.cache: str | None = None
        self.max_cache_age: int | None = None
        self.cache_manager: cache.CacheManager | None = None
        self.cache_instance: cache.Cache | None = None
        self.config_objects = config_objects or []
        self.post_processor = arg_postprocessor.ArgPostProcessor()

    @property
    def arg_converters(self) -> dict[str, Callable[[str], Any]]:
        """Get arg converters."""
        return self.post_processor.arg_converters

    @arg_converters.setter
    def arg_converters(self, value: dict[str, Callable[[str], Any]]):
        self.post_processor.arg_converters = value

    def _get_credentials(self) -> auth.Credentials:
        return self.plugins.cred_store.get_default()

    def expand_arg(self, arg: str) -> str:
        """Expand an arg to file content if prefixed with @."""
        return self.post_processor.expand_arg(arg)

    def check_args(self) -> List[str]:
        """Check the options instance and return issues as list."""
        return []

    def expand_args_typed(self, arg: str) -> Any:
        """Expand args with types."""
        return self.post_processor.expand_args_typed(arg)

    def expand_files_typed(self, args: Iterable[str]) -> List[Any]:
        """Load a list of files, typed by extension."""
        return self.post_processor.expand_files_typed(args)

    def expand_args_named(
        self,
        args: Iterable[str],
        expand_func: Callable[[str], Any] = (lambda s: s),
    ) -> dict[str, Any]:
        """Convert an arg list as assignments (key=value) into a dict."""
        return self.post_processor.expand_args_named(args, expand_func)

    def run(self) -> None:
        """Do the actual work.

        Override in subclass.
        """
        raise NotImplementedError()

    def _log_dry_run(self, msg: str):
        sys.stderr.write(f'**DRY RUN**: {msg}\n')

    def _log_verbose(self, msg: str):
        if self.verbose:
            sys.stderr.write(f'++Verbose++: {msg}\n')

    def _exception_to_status(self, e: Exception) -> Tuple[int, str] | None:
        """Map exception to command line return value and message."""
        if isinstance(e, UsageException):
            return 99, e.usage_text
        return None

    def _apply_args(self, options: argparse.Namespace) -> None:
        """Apply parsed arguments to self and config objects."""
        self.post_processor.namespace = options
        self.post_processor.apply_args(self, *self.config_objects)

    def main(self, args: Optional[List[str]] = None):
        """Execute it all.

        Used as main() function:
        ```
        if __name__ == '__main__':
            GmailCli().main()
        ```
        """
        if args is None:
            args = sys.argv[1:]
        options = self.arg_parser.parse_args(args)
        self._apply_args(options)

        levels = [logging.WARNING, logging.INFO, logging.DEBUG]
        if self.verbose > 2:
            self.verbose = 2
        logging.basicConfig(level=levels[self.verbose])

        cache_path = self.cache or os.environ.get("RX_LLM_PROC_CACHE")
        if cache_path:
            logging.info("Using cache file: %s", cache_path)
            default_age: cache.AgeSpec | None = None
            if self.max_cache_age is not None:
                default_age = {
                    'max_age_accessed': datetime.timedelta(
                        days=self.max_cache_age
                    )
                }
            self.cache_manager = cache.CacheManager(
                containers.LocalFileContainer(cache_path),
                default_age=default_age,
            )
            self.cache_instance = self.cache_manager.load_or_create()

        try:
            usage_issues = self.check_args()
            if usage_issues:
                usage_issue_str = "\n".join(
                    f'* {issue}' for issue in usage_issues
                )
                raise UsageException(usage_issue_str)

            try:
                self.run()
            finally:
                if self.cache_manager and self.cache_instance:
                    self.cache_manager.store(self.cache_instance)

        except UsageException as e:
            self.arg_parser.error(message=e.usage_text)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return_value, messsage = self._exception_to_status(e) or (
                100,
                f'Unexpected exception {e} encountered.\n',
            )
            sys.stderr.write(f'Execution failed: {messsage}\n')
            sys.exit(return_value)


class CommonDirOutputCli(CliBase):
    """Options for command line tools that create multiple files."""

    def _add_args(self):
        self.arg_parser.add_argument(
            '--output_dir',
            required=True,
            metavar='DIR_PATH',
            help='Directory under which the results are written.',
        )
        super()._add_args()

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        config_objects: List[Any] | None = None,
    ) -> None:
        """Create an instance."""
        super().__init__(creds, config_objects=config_objects)

        self.output_dir: str | None = None


class CommonFileOutputCli(CliBase):
    """Options for command line tools that create a single output file."""

    def _add_args(self):
        self.arg_parser.add_argument(
            '--output',
            '-o',
            type=str,
            metavar='FILENAME',
            help='Write output to FILENAME, not STDOUT',
        )
        super()._add_args()

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        config_objects: List[Any] | None = None,
    ) -> None:
        """Create instance."""
        super().__init__(creds, config_objects=config_objects)
        self.output: Optional[str] = None

    def write_output(self, contents: str | bytes):
        """Write to specified output file or STDOUT if not set."""
        if self.output:
            outfile_str = self.output
            if self.dry_run:
                self._log_dry_run(f"Write output to {outfile_str}")
            else:
                logging.info('Writing LLM output to %s', outfile_str)
                mode = 'w' if isinstance(contents, str) else 'wb'
                with open(outfile_str, mode) as outfile:
                    outfile.write(contents)
        else:
            if isinstance(contents, str):
                sys.stdout.write(contents)
            else:
                sys.stdout.buffer.write(contents)
