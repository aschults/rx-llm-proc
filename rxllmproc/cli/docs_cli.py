"""Docs CLI."""

import logging
import sys
import json
from rxllmproc.cli import cli_base
from rxllmproc.core import auth
from rxllmproc.docs import api as docs_api
from rxllmproc.docs import docs_model
from rxllmproc.docs import types as docs_types
from rxllmproc.docs import markdown_to_gdocs
from rxllmproc.core.infra import utilities
from rxllmproc.docs import section
from rxllmproc.docs import llm_updater
from rxllmproc.docs import operators as doc_ops
from rxllmproc.llm import api as llm_api


class DocsCli(cli_base.CommonFileOutputCli):
    """Command line implementation for Docs wrapper."""

    def _add_args(self):
        self.arg_parser.description = "Access Google Docs via Command line."
        subparsers = self.arg_parser.add_subparsers(
            dest="command",
            help="Operation to perform on Docs",
            metavar="OPERATION",
            description="Operations to perform on Docs.",
        )
        insert_subcommand = subparsers.add_parser(
            "insert",
            help="Insert content into a document.",
            description="Insert text or markdown into a Google Doc.",
        )
        insert_subcommand.add_argument(  # This is common to all location options
            "--document_id",
            required=True,
            help="The ID of the document to modify.",
        )

        location_group = insert_subcommand.add_mutually_exclusive_group(
            required=False
        )
        location_group.add_argument(
            "--at_start",
            action="store_true",
            help="Insert text at the beginning of the document body (index 1).",
        )
        location_group.add_argument(
            "--at_end",
            action="store_true",
            help="Insert text at the end of the document body.",
        )
        location_group.add_argument(
            "--at_index",
            type=int,
            help="The specific index where text insertion should begin.",
        )
        location_group.add_argument(
            "--section_start",
            action="store_true",
            help="Insert at the start of the section identified by --section.",
        )
        location_group.add_argument(
            "--section_end",
            action="store_true",
            help="Insert at the end of the section identified by --section.",
        )
        location_group.add_argument(
            "--section_replace",
            action="store_true",
            help="Replace the body of the section identified by --section.",
        )
        location_group.add_argument(
            "--instructions",
            help=(
                "Instructions for LLM-based update. Alternative to location arguments. "
                "Variable `content` is provided containing the input file or stream in "
                "addition to any template variables defined with --define."
            ),
        )

        insert_subcommand.add_argument(
            "--section",
            action="append",
            help="Regex to identify a section. Can be used multiple times for hierarchical search.",
        )
        insert_subcommand.add_argument(
            "--heading_id",
            help="The heading ID of the section to target.",
        )
        insert_subcommand.add_argument(
            "--plaintext",
            action="store_true",
            help="Treat input content as plain text, not Markdown.",
        )
        insert_subcommand.add_argument(
            "--ensure-newline",
            action="store_true",
            help="Ensure the insertion happens on a new line.",
        )
        insert_subcommand.add_argument(
            "--model",
            default="gemini",
            help="LLM model to use for instructions.",
        )
        insert_subcommand.add_argument(
            "-D",
            "--define",
            action="append",
            help="Define template variables key=value for the instructions.",
        )
        insert_subcommand.add_argument(
            "file",
            nargs="?",
            metavar="INPUT_FILE",
            help="Read content to insert from file, not STDIN.",
        )
        insert_subcommand.add_argument(
            "--dry_run",
            action="store_true",
            help="Execute but don't change anything, logging request to stderr.",
        )

        get_subcommand = subparsers.add_parser(
            "get",
            help="Get a document as JSON.",
            description="Downloads the full document object as JSON.",
        )
        get_subcommand.add_argument(
            "--document_id",
            required=True,
            help="The ID of the document to get.",
        )
        get_subcommand.add_argument(
            "--output",
            "-o",
            type=str,
            metavar="FILENAME",
            help="Write output to FILENAME, not STDOUT",
        )
        get_subcommand.add_argument(
            "--nested",
            action="store_true",
            help="Output the document structure as nested sections.",
        )
        super()._add_args()

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        docs_wrapper: docs_api.DocsWrapper | None = None,
    ) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__(creds)
        self.command: str | None = None
        self.document_id: str | None = None
        self.plaintext: bool = False
        self.file: str | None = None
        self.at_index: int | None = None
        self.at_start: bool = False
        self.at_end: bool = False
        self.ensure_newline: bool = False
        self.section: list[str] | None = None
        self.heading_id: str | None = None
        self.section_start: bool = False
        self.section_end: bool = False
        self.section_replace: bool = False
        self.nested: bool = False
        self._wrapper = docs_wrapper
        self.instructions: str | None = None
        self.model: str = "gemini"
        self.define: list[str] | None = None

    @property
    def wrapper(self) -> docs_api.DocsWrapper:
        """Get the Docs wrapper."""
        if self._wrapper is None:
            self._wrapper = docs_api.DocsWrapper(self._get_credentials())
        return self._wrapper

    def _determine_insert_index(
        self, doc: docs_model.Document, target_section: section.Section | None
    ) -> int:
        """Determines the insertion index and handles section replacement."""
        if self.section_start:
            if not target_section:
                raise cli_base.UsageException(
                    "--section_start requires --section or --heading_id"
                )
            return target_section.end
        elif self.section_end:
            if not target_section:
                raise cli_base.UsageException(
                    "--section_end requires --section or --heading_id"
                )
            return target_section.subsections_end
        elif self.section_replace:
            if not target_section:
                raise cli_base.UsageException(
                    "--section_replace requires --section or --heading_id"
                )
            # If it's a text section (no heading), replace the whole thing.
            # If it's a heading section, replace the body (keep heading).
            if target_section.level == "text":
                start_idx = target_section.start
                end_idx = target_section.end
            else:
                start_idx = target_section.end
                end_idx = target_section.subsections_end

            if end_idx > start_idx:
                if self.dry_run:
                    self._log_dry_run(
                        f"Would delete range {start_idx}-{end_idx}"
                    )
                else:
                    doc.delete_range(start_idx, end_idx)
            return start_idx
        elif self.at_start:
            return doc.get_start()
        elif self.at_index is not None:
            return self.at_index
        elif self.at_end:
            return doc.get_end()

        return doc.get_start()

    def _run_insert(self):
        """Handles the 'insert' command."""
        if not self.document_id:
            raise cli_base.UsageException("document_id is required")

        doc = docs_model.Document(self.wrapper, self.document_id)

        content = (
            sys.stdin.read() if self.file is None else open(self.file).read()
        )

        if self.instructions:
            if self.section or self.heading_id:
                raise cli_base.UsageException(
                    "Cannot use --section or --heading_id with --instructions."
                )

            llm = llm_api.create_model(
                self.model, cache_instance=self.cache_instance
            )
            updater = llm_updater.DocUpdater(
                doc, self.expand_arg(self.instructions), llm
            )

            template_vars = self.expand_args_named(
                self.define or [], self.expand_args_typed
            )

            operations = updater.generate(content=content, **template_vars)

            if self.dry_run:
                self._log_dry_run(
                    f"Would execute {len(operations)} operations on {self.document_id}"
                )
                sys.stderr.write(
                    json.dumps(
                        [utilities.asdict(op) for op in operations], indent=2
                    )
                    + "\n"
                )
            else:
                logging.info(
                    "Executing %d operations on document %s",
                    len(operations),
                    self.document_id,
                )
                editor = doc_ops.BatchEditor(doc)
                for op in operations:
                    editor.add(op)
                editor.execute()
            return

        if not (
            self.at_start
            or self.at_end
            or self.at_index is not None
            or self.section_start
            or self.section_end
            or self.section_replace
        ):
            raise cli_base.UsageException(
                "One of --at_start, --at_end, --at_index, --section_start, --section_end, --section_replace or --instructions is required."
            )

        target_section = doc.find_section(self.section, self.heading_id)
        if (self.section or self.heading_id) and not target_section:
            raise cli_base.UsageException("Specified section not found.")

        insert_index = self._determine_insert_index(doc, target_section)

        if self.dry_run:
            if not self.plaintext:
                requests = markdown_to_gdocs.convert_markdown_to_requests(
                    content
                )
            else:
                requests = [
                    docs_types.DocsRequest(
                        insertText=docs_types.InsertTextRequest(
                            text=content, location=docs_types.Location(index=0)
                        )
                    )
                ]
            doc.adjust_requests_indices(requests, insert_index)
            self._log_dry_run(
                f"Would insert {len(requests)} requests into document {self.document_id} at index {insert_index}"
            )
            sys.stderr.write(
                json.dumps(utilities.asdict(requests), indent=2) + "\n"
            )
        else:
            logging.info(
                "Inserting content into document %s",
                self.document_id,
            )
            if self.plaintext:
                doc.insert_at(
                    insert_index, content, ensure_newline=self.ensure_newline
                )
            else:
                doc.insert_markdown_at(
                    insert_index, content, ensure_newline=self.ensure_newline
                )

    def _run_get(self):
        """Handles the 'get' command."""
        if not self.document_id:
            raise cli_base.UsageException(
                "document_id is required for get command"
            )
        document = self.wrapper.get(self.document_id)
        if self.nested:
            if not document.body:
                self.write_output("[]")
                return
            content = docs_model.DocumentContent(document.body)
            self.write_output(
                json.dumps([s.as_dict() for s in content.sections], indent=2)
            )
        else:
            self.write_output(json.dumps(utilities.asdict(document), indent=2))

    def run(self):
        """Execute the action."""
        if self.command == "insert":
            self._run_insert()
        elif self.command == "get":
            self._run_get()
        else:
            raise cli_base.UsageException("Unknown command")


def main():
    """Run the command line tool."""
    DocsCli().main()


if __name__ == "__main__":
    main()
