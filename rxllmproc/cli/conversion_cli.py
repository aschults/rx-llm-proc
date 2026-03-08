"""CLI for converting between different file formats."""

import sys
import mimetypes
import logging

from rxllmproc.cli import cli_base
from rxllmproc.text_processing import converters


class ConversionCli(cli_base.CommonFileOutputCli):
    """Command line implementation for file format conversion."""

    def _add_args(self):
        self.arg_parser.description = (
            "A versatile tool to convert between different file formats."
        )
        self.arg_parser.add_argument(
            "input",
            nargs="?",
            metavar="INPUT_FILE",
            help="Read from INPUT_FILE. If not provided, reads from STDIN.",
        )
        self.arg_parser.add_argument(
            "--from-mime-type",
            help="MIME type of the input. Overrides detection from filename.",
        )
        self.arg_parser.add_argument(
            "--to-mime-type",
            help="MIME type for the output. Overrides detection from filename.",
        )
        super()._add_args()

    def __init__(self) -> None:
        """Construct the instance."""
        super().__init__()
        self.input: str | None = None
        self.from_mime_type: str | None = None
        self.to_mime_type: str | None = None

    def run(self):
        """Execute the conversion."""
        # Determine input and output MIME types
        from_mime = self.from_mime_type
        if not from_mime and self.input:
            from_mime, _ = mimetypes.guess_type(self.input)

        to_mime = self.to_mime_type
        if not to_mime and self.output:
            to_mime, _ = mimetypes.guess_type(self.output)

        if not from_mime:
            raise cli_base.UsageException(
                "Cannot determine input MIME type. Please use --from-mime-type."
            )
        if not to_mime:
            raise cli_base.UsageException(
                "Cannot determine output MIME type. Please use --to-mime-type."
            )

        # Read input
        input_content: str
        if self.input:
            logging.info("Reading from file: %s", self.input)
            with open(self.input, "r", encoding="utf-8") as f:
                input_content = f.read()
        else:
            logging.info("Reading from STDIN.")
            input_content = sys.stdin.read()

        # Perform conversion
        output_content = self._convert(input_content, from_mime, to_mime)

        # Write output
        self.write_output(output_content)

    def _convert(self, content: str, from_mime: str, to_mime: str) -> str:
        """Selects and runs the appropriate conversion function."""
        logging.info("Converting from %s to %s", from_mime, to_mime)

        if from_mime == "text/html" and to_mime == "text/markdown":
            return converters.convert_html_to_markdown(content)

        # Add other conversion paths here in the future
        # elif from_mime == '...' and to_mime == '...':
        #     return ...

        raise cli_base.UsageException(
            f"Conversion from '{from_mime}' to '{to_mime}' is not supported."
        )


def main():
    """Run the command line tool."""
    ConversionCli().main()


if __name__ == "__main__":
    main()
