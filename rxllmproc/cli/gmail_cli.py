"""GMail query and message download CLI."""

import os
from os import path
import json
import logging

from rxllmproc.cli import cli_base
from rxllmproc.gmail import types as gmail_types
from rxllmproc.app.mail import index
from rxllmproc.text_processing import email_processing
from rxllmproc.core import auth
from rxllmproc.gmail.api import GMailWrap
from rxllmproc.core.infra.utilities import asdict


class GmailCli(cli_base.CommonDirOutputCli):
    """Command line implementation for GMail wrapper."""

    def _add_args(self):
        self.arg_parser.description = "Access Email messages in GMail."
        subparsers = self.arg_parser.add_subparsers(
            dest="command",
            help="Operation to perform on GMail",
            metavar="OPERATION",
            description="Operations to perform with GMail",
        )
        get_subcommand = subparsers.add_parser(
            "get_all",
            help="Get all Email messages matching a GMail query",
            description=(
                "Get all Email messages matching the provided query "
                "and save them to a directory, named by ID."
            ),
        )
        get_subcommand.add_argument(
            "query",
            metavar="GMAIL_SEARCH_QUERY",
            help="All messages matching this query are downloaded.",
        )
        get_subcommand.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="If set, overwrite files if they exist.",
        )
        get_subcommand.add_argument(
            "--output_dir",
            required=True,
            metavar="DIR_PATH",
            help="Directory under which the results are written.",
        )
        get_subcommand.add_argument(
            "--dry_run",
            action="store_true",
            help="Execute but don't change anything.",
        )
        get_subcommand.add_argument(
            "--with_index",
            action="store_true",
            help="Execute but don't change anything.",
        )
        get_subcommand.add_argument(
            "--by_thread",
            action="store_true",
            help="If set, create subdirectories for each thread.",
        )
        get_subcommand.add_argument(
            "--to_markdown",
            action="store_true",
            help="If set, convert email body to Markdown and save as .md files.",
        )

        # Note: Skipping the output option as we're adding directly.
        cli_base.CliBase._add_args(self)

    def __init__(
        self,
        creds: auth.CredentialsFactory | None = None,
        gmail_wrap: GMailWrap | None = None,
    ) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__(creds)

        self.force = False
        self.with_index = False
        self.by_thread = False
        self.to_markdown = False
        self.command: str | None = None
        self._wrapper = gmail_wrap
        self.max_results: int = -1
        self.query: str | None = None
        self.index_manager: index.GmailIndexManager | None = None

    @property
    def wrapper(self) -> GMailWrap:
        """Get the Drive wrapper."""
        if self._wrapper is None:
            self._wrapper = GMailWrap(self._get_credentials())
        return self._wrapper

    def _process_single_email(self, msg_id: gmail_types.MessageId):
        """Process a single email message: download, save, and index it."""
        if self.output_dir is None:
            # This should have been checked before calling.
            raise cli_base.UsageException("No output dir specified")

        ext = ".md" if self.to_markdown else ".msg"
        rel_path = f"{msg_id.id}{ext}"
        if self.by_thread and msg_id.threadId:
            rel_path = path.join(msg_id.threadId, rel_path)

        output_file = path.join(self.output_dir, rel_path)
        output_dir = path.dirname(output_file)
        if not path.exists(output_dir):
            os.makedirs(output_dir)

        file_exists = path.isfile(output_file)

        if (
            not self.force
            and file_exists
            and (self.index_manager is None or msg_id.id in self.index_manager)
        ):
            logging.info(
                "Skipping message %s as file already exists and is indexed",
                repr(msg_id.id),
            )
            return

        log_message = f"Writing msg {repr(msg_id)} to file {repr(output_file)}"
        if self.dry_run:
            self._log_dry_run(log_message)
            return

        try:
            gmail_msg: gmail_types.Message = self.wrapper.get(msg_id.id)
            if self.to_markdown:
                content = email_processing.get_email_content(
                    gmail_msg.parsed_msg, output="md"
                )
            else:
                content = gmail_msg.parsed_msg.as_string()

            with open(output_file, "w", encoding="utf-8") as outfile:
                self._log_verbose(log_message)
                outfile.write(content)

            meta_file_path = path.join(output_dir, f"{msg_id.id}.meta.json")
            logging.info("Saving metadata to %s", meta_file_path)
            msg_dict = asdict(gmail_msg)
            msg_dict.pop("parsed_msg", None)
            msg_dict.pop("raw", None)
            with open(meta_file_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "headers": [
                            {"name": k, "value": v}
                            for k, v in gmail_msg.parsed_msg.items()
                        ],
                        "api_response": msg_dict,
                    },
                    f,
                    indent=4,
                )
            if self.index_manager is not None:
                self.index_manager.add(gmail_msg, path=rel_path)

        except Exception:
            logging.error(
                "Failed to process message %s", msg_id.id, exc_info=True
            )
            raise

    def _run_get_all(self):
        """Execute the get_all action, download messages."""
        if self.output_dir is None:
            raise cli_base.UsageException("No output dir specified")

        if self.query is None:
            raise cli_base.UsageException("Need to pass query")

        if self.with_index:
            self.index_manager = index.GmailIndexManager(self.output_dir)

        result_count = 0
        for msg_id in self.wrapper.search(self.query):
            if self.max_results >= 0 and result_count >= self.max_results:
                break
            result_count += 1
            self._process_single_email(msg_id)
            if self.index_manager is not None and result_count % 100 == 0:
                self.index_manager.save_index()

        if self.index_manager is not None:
            self.index_manager.save_index()

    def run(self):
        """Execute the action, download messages."""
        if self.command == "get_all":
            self._run_get_all()
        else:
            raise cli_base.UsageException(f"Unknown command: {self.command}")


def main():
    """Run the command line tool."""
    GmailCli().main()


if __name__ == "__main__":
    main()
