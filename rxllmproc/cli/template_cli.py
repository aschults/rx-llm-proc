"""Templating CLI."""

from typing import List, Optional

from rxllmproc.cli import cli_base
from rxllmproc.text_processing import jinja_processing


class TemplateCli(cli_base.CommonFileOutputCli):
    """Command line implementation of Jinja template renderer."""

    def _add_args(self):
        self.arg_parser.add_argument('--template')
        self.arg_parser.add_argument(
            '-D', '--define', action='append', dest='vars'
        )
        self.arg_parser.add_argument('args', action='extend', nargs='*')
        return super()._add_args()

    def __init__(self) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__()

        self.processor = jinja_processing.JinjaProcessing()
        self._template = None

        self.template: Optional[str] = None
        self.vars: List[str] | None = None
        self.args: List[str] | None = None

    def run(self):
        """Execute the action, render the template."""
        if self.template is None:
            raise cli_base.UsageException('No template passed.')
        self.processor.set_template(self.expand_arg(self.template))
        kwargs = self.expand_args_named(self.vars or [], self.expand_args_typed)
        args = self.expand_files_typed(self.args or [])
        kwargs['args'] = args
        result = self.processor.render(**kwargs)
        self.write_output(result)


def main():
    """Run the command line tool."""
    TemplateCli().main()


if __name__ == '__main__':
    main()
