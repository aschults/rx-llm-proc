"""Common base for LLM CLI."""

from os import path
import os
from typing import List, Set, Dict, Any, Tuple, Union, Callable
import glob
import json
import requests
import datetime
import sys
import logging
import re

import pydantic_ai

from rxllmproc.cli import cli_base
from rxllmproc.core import auth

from rxllmproc.llm import api as llm_api
from rxllmproc.text_processing import jinja_processing
from rxllmproc.core.infra import containers


def glob_to_regex(glob_pattern: str) -> re.Pattern[str]:
    """Translate a recursive glob pattern into a regular expression.

    Args:
        glob_pattern: The glob pattern to translate.

    Returns:
        The equivalent regular expression string.
    """
    # Escape special characters in the glob pattern
    escaped_pattern = re.escape(glob_pattern)

    # Replace glob special characters with their regex equivalents
    regex_pattern = escaped_pattern.replace(
        r'\*\*', r'(?:.*?)?'
    )  # Handle recursive '**'
    regex_pattern = regex_pattern.replace(r'\*', r'[^/]*')  # Handle single '*'
    regex_pattern = regex_pattern.replace(r'\?', r'.')  # Handle '?'

    # Add anchors to match the entire string
    regex_pattern = f'^{regex_pattern}$'

    return re.compile(regex_pattern)


class LlmCli(cli_base.CommonFileOutputCli):
    """Command line implementation for GMail wrapper."""

    def list_files(self, pattern: str) -> Dict[str, Any]:
        """List all context files, called by the LLM."""
        result = list(
            self.context_files_expanded.intersection(
                glob.iglob(pattern, recursive=True)
            )
        )
        logging.info('Listing files to LLM: %s', repr(result))
        return {
            'pattern': pattern,
            'files': result,
            'success': 'All files listed',
        }

    def get_time(self) -> Dict[str, Any]:
        """Get file content, called by the LLM."""
        logging.info(
            'Returning current time to LLM: %s', str(datetime.datetime.now())
        )
        return {'current_time': str(datetime.datetime.now())}

    def retreive_file(self, filename: str) -> Dict[str, Any]:
        """Get file content, called by the LLM."""
        filename = path.normpath(filename)

        if filename not in self.context_files_expanded or not path.isfile(
            path=filename
        ):
            logging.info('File %s not found for LLM', filename)
            logging.debug(
                'Available files: %s', repr(self.context_files_expanded)
            )
            return {
                'file_not_found': 'The requested file does not exist.',
                'filename': filename,
            }
        with open(filename, 'r') as infile:
            contents = infile.read()
            logging.info(
                'File content for %s to LLM: %s', filename, repr(contents)
            )
            return {
                'success': 'The file was read completely',
                'filename': filename,
                'contents': contents,
            }

    def write_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Get file content, called by the LLM."""
        filename = path.normpath(filename)
        filename2 = path.relpath(filename)
        if not any(
            (write_re.fullmatch(filename) or write_re.fullmatch(filename2))
            for write_re in self.writeable_files_regex
        ):
            logging.info('File %s is not in writable files', filename)
            return {
                'no_permissions': 'Not permitted to write file',
                'filename': filename,
                'content': None,
            }

        basedir = path.dirname(filename)
        if basedir:
            os.makedirs(basedir, exist_ok=True)
        with open(filename, 'w') as outfile:
            outfile.write(content)
            logging.info(
                'Writing file %s for LLM, content: %s', filename, repr(content)
            )
            return {
                'success': 'File completely written.',
                'content': content,
                'filename': filename,
            }

    def retreive_url(self, url: str) -> Dict[str, Any]:
        """Get any URL, called by the LLM."""
        response = requests.get(url)
        if response.status_code < 200 or response.status_code >= 300:
            return {'status': 'failed', 'url': url}
        return {
            'status': 'OK',
            'url': url,
            'mime-type': response.headers['Content-Type'],
            'contents': response.text,
        }

    def _add_args(self):
        self.arg_parser.add_argument(
            '--model',
            '-M',
            metavar='LLM_MODEL_NAME',
            default='gemini',
            help='Sets the model name to use as LLM. Default: gemini',
        )
        self.arg_parser.add_argument(
            '--context_files',
            action='append',
            metavar='FILENAME_GLOB',
            help='Glob of filenames to expose to the LLM.',
        )
        self.arg_parser.add_argument(
            '--writeable_files',
            action='append',
            metavar='FILENAME_GLOB',
            help='Glob of filenames that the LLM can write into.',
        )
        self.arg_parser.add_argument(
            '--enable_list_files',
            action='store_true',
            help='Is set, allows the LLM to get a list of all context files.',
        )
        self.arg_parser.add_argument(
            '--enable_fetch_url',
            action='store_true',
            help='If set, the LLM can fetch web content by URL.',
        )
        self.arg_parser.add_argument(
            '--api_key',
            metavar='API_KEY',
            help='API key to use for authentication.',
        )
        self.arg_parser.add_argument(
            'prompts',
            action='extend',
            nargs='*',
            metavar='LLM_TEXT_PROMPT',
            help='Prompt (text) to be concatenated an evaluated.',
        )
        self.arg_parser.add_argument(
            '--as_json',
            '-j',
            action='store_true',
            help='If set, instruct the LLM to return a JSON object.',
        )
        super()._add_args()
        self.arg_parser.add_argument(
            '--upload',
            action='append',
            metavar='FILE_PATH',
            help='Upload a local file to be included in the prompt.',
        )
        self.arg_parser.add_argument(
            '-D',
            '--define',
            action='append',
        )

    def __init__(self, creds: auth.CredentialsFactory | None = None) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        self.context_files_expanded: Set[str] = set()
        self.writeable_files_regex: list[re.Pattern[str]] = []

        super().__init__(creds)

        self.processor = jinja_processing.JinjaProcessing()

        self.context_files: List[str] | None = None
        self.writeable_files: List[str] | None = None
        self.prompts: List[str] = []
        self.enable_list_files = False
        self.enable_fetch_url = False
        self.as_json = False
        self.model = 'gemini'
        self.api_key: str | None = None
        self.upload: List[str] | None = None
        self.define: List[str] | None = None

        current_time = pydantic_ai.Tool(
            self.get_time,
            name='get_current_time',
            description='Gets the current local time.',
        )

        self.functions: list[Union[pydantic_ai.Tool, Callable[..., Any]]] = [
            current_time
        ]

    def _include_file(self, filename: str) -> str:
        """Jinja function to include a file's content."""
        return self.expand_arg(f'@{filename}')

    def _add_functions(self):
        """Add functions based on set options."""
        file_func = pydantic_ai.Tool(
            self.retreive_file,
            name='read_file',
            description='Read the full content of the specified file.',
        )
        file_write_func = pydantic_ai.Tool(
            self.write_file,
            name='write_file',
            description='Write the content of the specified file.',
        )
        list_func = pydantic_ai.Tool(
            self.list_files,
            name='list_files',
            description='List files by glob/unix style pattern.',
        )
        get_url_func = pydantic_ai.Tool(
            self.retreive_url,
            name='get_url',
            description='Gets the content of an external website or URL.',
        )

        if self.context_files_expanded:
            self.functions.append(file_func)
        if self.writeable_files_regex:
            self.functions.append(file_write_func)
        if self.enable_list_files:
            self.functions.append(list_func)
        if self.enable_fetch_url:
            self.functions.append(get_url_func)

    def check_args(self) -> List[str]:
        """Check the passed arguments.

        Allow multiple positional args.
        """
        return []

    def _build_model(self) -> llm_api.LlmBase:
        logging.info(
            'Creating LLM of type %s, functions: %s',
            self.model,
            repr(self.functions),
        )
        return llm_api.create_model(
            self.model,
            functions=self.functions,
            api_key=self.api_key,
            cache_instance=self.cache_instance,
        )

    def _exception_to_status(self, e: Exception) -> Tuple[int, str] | None:
        """Map Generator Errors to 30 exit value."""
        if isinstance(e, llm_api.GeneratorError):
            return 30, f'Could not generate result: {e}'
        return super()._exception_to_status(e)

    def _parse_container_specs(self) -> List[containers.Container]:
        """Parse container specifications from --upload arguments."""
        if not self.upload:
            return []

        return [
            containers.LocalFileContainer(path) for path in self.upload if path
        ]

    def run(self):
        """Execute the action, download messages."""
        for opt_filename in self.context_files or []:
            for filename in glob.iglob(opt_filename, recursive=True):
                self.context_files_expanded.add(filename)
                self.context_files_expanded.add(os.path.abspath(filename))
        self.writeable_files_regex = [
            glob_to_regex(pattern) for pattern in self.writeable_files or []
        ]
        self.processor.add_global('include_file', self._include_file)

        self._add_functions()

        template_vars = self.expand_args_named(
            self.define or [], self.expand_args_typed
        )

        prompt_parts: List[Any] = []
        if self.prompts:
            for arg in self.prompts:
                self.processor.set_template(self.expand_arg(arg))
                prompt_parts.append(self.processor.render(**template_vars))
        else:
            stdin_str = sys.stdin.read()
            if not stdin_str:
                raise cli_base.UsageException(
                    'Either provide prompt on STDIN or as positional arguments.'
                )
            self.processor.set_template(stdin_str)
            prompt_parts.append(self.processor.render(**template_vars))

        prompt_parts.extend(self._parse_container_specs())

        model = self._build_model()
        if self.as_json:
            response_obj = model.query_json(*prompt_parts)
            response = json.dumps(response_obj, indent=1)
        else:
            response = model.query(*prompt_parts)

        if not response.endswith('\n'):
            response += '\n'
        self.write_output(response)


def main():
    """Run the command line tool."""
    LlmCli().main()


if __name__ == '__main__':
    main()
