"""CLI for categorizing emails using reactive operators."""

import logging
import sys
import threading

from rxllmproc.cli import cli_base
from rxllmproc.app.mail import types as mail_types
from rxllmproc.core.infra import collector
from rxllmproc.app import environment as app_environment
from rxllmproc.database import operators as sql_operators
from rxllmproc.app.mail import processing as mail_processing
from rxllmproc.app.docs import processing as docs_processing
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.gmail import types as gmail_types
from rxllmproc.app.docs import types as docs_types

_DB_CLASSES = [
    gmail_types.Message,
    mail_types.MailMetadata,
    analysis_types.ActionItem,
    analysis_types.ActionItemPlacement,
    analysis_types.Source,
    mail_types.MailSource,
    analysis_types.Analysis,
]


class RxMailCategorizerCli(cli_base.CliBase):
    """CLI to categorize emails using Rx operators."""

    def _add_args(self):
        """Add command line arguments."""
        self.arg_parser.description = "Categorize emails using Rx pipeline."
        self.arg_parser.add_argument(
            "--gmail_query", help="Gmail query to fetch emails."
        )
        self.arg_parser.add_argument(
            "--categorization_template",
            help=(
                "Jinja2 template for the categorization. "
                "The default template supports the following variables: "
                "categories_instructions, action_items_instructions and context_instructions."
                "It will also receive: email_metadata, email_content."
            ),
        )
        self.arg_parser.add_argument(
            "--categories_instructions",
            default="No details provided.",
            help="Categories instructions for the categorization template.",
        )
        self.arg_parser.add_argument(
            "--action_items_instructions",
            default="No details provided.",
            help="Action items instructions for the default template.",
        )
        self.arg_parser.add_argument(
            "--context_instructions",
            default="No details provided.",
            help="Personal context for the default template.",
        )
        self.arg_parser.add_argument(
            "--model", default="gemini-lite", help="LLM model to use."
        )
        self.arg_parser.add_argument(
            "--db_url",
            default="sqlite:///mail_data.db",
            help="SQLAlchemy URL for the database.",
        )
        self.arg_parser.add_argument(
            "-D",
            "--define",
            action="append",
            help="Define template variables key=value.",
        )
        self.arg_parser.add_argument(
            "--force_all",
            action="store_true",
            help="Force processing of all emails, ignoring existing index.",
        )
        self.arg_parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Interval in seconds to check for new emails. Set to 0 to run once.",
        )
        self.arg_parser.add_argument(
            "--todo_doc_id",
            help="Google Doc ID to insert action items into.",
        )
        self.arg_parser.add_argument(
            "--docs_batch_size",
            type=int,
            default=5,
            help="Batch size for docs processing.",
        )
        self.arg_parser.add_argument(
            "--priority_re",
            default=r'.*',
            help="Regex for priority filtering in docs.",
        )
        self.arg_parser.add_argument(
            "--docs_todo_template",
            help="Llm Prompt template for docs markdown.",
        )
        self.arg_parser.add_argument(
            "--docs_insertion_instructions",
            help="Llm instructions on how ti insert todos in the doc.",
        )
        super()._add_args()

    def __init__(self) -> None:
        """Initialize the CLI."""
        super().__init__()
        self.mail_config = mail_types.MailConfig()
        self.docs_config = docs_types.DocsConfig()
        self.config_objects.append(self.mail_config)
        self.config_objects.append(self.docs_config)
        self.model: str = "gemini-lite"
        self.db_url: str = "sqlite:///mail_data.db"
        self._collector = collector.MemoryCollector()
        self.errors: list[Exception] = []
        self._db: sql_operators.RxDatabase | None = None

    @property
    def db(self) -> sql_operators.RxDatabase:
        """Get the database instance."""
        if self._db is None:
            self._db = sql_operators.RxDatabase(
                self.db_url,
                _DB_CLASSES,
            )
        return self._db

    def check_args(self) -> list[str]:
        """Check arguments."""
        issues = super().check_args()
        if (
            not self.mail_config.gmail_query
            and not self.docs_config.todo_doc_id
        ):
            issues.append(
                "At least one of --gmail_query or --todo_doc_id must be provided."
            )
        return issues

    def error_handler(self, e: Exception):
        """Handle errors."""
        self.errors.append(e)

    def _excepthook(self, args: threading.ExceptHookArgs):
        """Handle threading exceptions."""
        logging.error("Uncaught threading exception", exc_info=args.exc_value)
        sys.exit(99)

    def run(self):
        """Execute the pipeline."""
        threading.excepthook = self._excepthook

        self._collector.start()

        env = app_environment.RxEnvironment(
            db=self.db,
            model_name=self.model,
            creds_factory=self.plugins.cred_store,
            cache_instance=self.cache_instance,
            collector=self._collector,
            error_handler=self.error_handler,
        )

        mail_processor = None
        if self.mail_config.gmail_query:
            mail_processor = mail_processing.MailProcessing(
                env=env,
                config=self.mail_config,
            )

        docs_processor = None
        if self.docs_config.todo_doc_id:
            docs_processor = docs_processing.DocsProcessing(
                env=env, config=self.docs_config
            )
        else:
            logging.info("No todo_doc_id provided, skipping docs exporting.")

        # 1. Trigger
        if mail_processor:
            mail_processor.start_pipeline()
        if docs_processor:
            docs_processor.start_pipeline()

        try:
            if mail_processor:
                mail_processor.join_pipeline()
            if docs_processor:
                docs_processor.join_pipeline()
        except KeyboardInterrupt:
            logging.info("Stopping pipelines...")
            if mail_processor:
                mail_processor.stop_pipeline(safe=False)
            if docs_processor:
                docs_processor.stop_pipeline(safe=False)

        if self.errors:
            raise self.errors[0]


def main():
    """Run the command line tool."""
    RxMailCategorizerCli().main()


if __name__ == "__main__":
    main()
