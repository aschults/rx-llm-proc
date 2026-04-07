"""Reactive pipeline for mail processing."""

import logging
from typing import Any, Callable

import reactivex as rx
from reactivex import operators as ops
from reactivex.abc import scheduler as rx_abc_scheduler
from reactivex import scheduler as rx_scheduler
import sqlalchemy

from rxllmproc.gmail import types as gmail_types
from rxllmproc.gmail import operators as gmail_operators
from rxllmproc.llm import operators as llm_operators
from rxllmproc.database import operators as sql_operators
from rxllmproc.text_processing import operators as template_operators
from rxllmproc.app import environment as app_environment
from rxllmproc.app.analysis import types as analysis_types
from rxllmproc.app.mail import types

_CATEGORIZATION_TEMPLATE = """
## Instructions

You are my trusted assistant, helping me to keep track of what is happening in my emails.
You will categorize emails and extract action items and noteworthy details from them, based on
the category descriptions, Action item instructions and my personal context below.

## Categories

{{categories_instructions | render}}

## Action Item Instructions

{{action_items_instructions | render}}

## Personal Context

{{context_instructions | render}}

## Result

Reply in JSON format, based on the schema provided in the request. Do not include any other text.

## Email Data

### Email metadata:
{{email_metadata}}

-------
### Email Message:

{{email_content}}
"""


class MailPipeline:
    """Reactive pipeline for mail processing."""

    def __init__(
        self,
        config: types.MailPipelineConfig,
        env: app_environment.RxEnvironment | None = None,
        scheduler: rx_abc_scheduler.SchedulerBase | None = None,
        db: sql_operators.RxDatabase | None = None,
    ) -> None:
        """Initialize the mail pipeline."""
        self.scheduler = scheduler or rx_scheduler.ThreadPoolScheduler(5)
        # Preserve a local environment as it won't be in scope anymore later.
        self.env = env or app_environment.shared().update()
        self.config = config
        self.db = db or self.env.db

    def _make_query_dict(self, msg: gmail_types.Message) -> dict[str, Any]:
        headers = [
            f'{k}: {msg.parsed_msg.get(k)}'
            for k in ("Subject", "From", "To", "Cc", "Bcc", "Received")
            if k in msg.parsed_msg
        ]
        return {
            'email_content': msg.markdown_body,
            'email_metadata': "\n".join(headers),
        }

    def _catch_error(
        self, e: Exception, _: rx.Observable[Any]
    ) -> rx.Observable[Any]:
        logging.error("Error in processing pipeline", exc_info=e)
        self.env.error_handler(e)
        return rx.empty()

    def get_gmail_ids(self) -> set[str]:
        """Get the set of Gmail IDs that have already been processed."""
        mail_metadata_table = self.db.metadata.tables['mail_metadata']
        stmt = sqlalchemy.select(mail_metadata_table.c.id)
        return set(self.db.session.execute(stmt).scalars().all())

    def analyze_email(
        self,
    ) -> Callable[
        [rx.Observable[gmail_types.Message]], rx.Observable[types.MailSource]
    ]:
        """Analyze an email message to extract structured data."""

        def _analyze_email(
            source: rx.Observable[gmail_types.Message],
        ) -> rx.Observable[types.MailSource]:
            def _process(
                msg: gmail_types.Message,
            ) -> rx.Observable[types.MailSource]:
                mail_metadata = types.MailMetadata.from_msg(msg)

                obs = rx.of(msg)
                if self.scheduler:
                    obs = obs.pipe(ops.observe_on(self.scheduler))

                obs = obs.pipe(
                    ops.map(self._make_query_dict),
                    template_operators.TemplateBuilder(
                        self.config.template_content
                    )
                    .add_globals(**self.config.template_parameters)
                    .create(),
                    llm_operators.generate_object(
                        model=self.env.model_name,
                        result_type=analysis_types.Analysis,
                    ),
                    ops.map(
                        lambda analysis: types.MailSource(  # pytype: disable=wrong-keyword-args
                            id=mail_metadata.url,
                            mail_metadata=mail_metadata,
                            analysis=analysis,
                        )
                    ),
                    self.env.collect('analyzed mails'),
                )

                obs = obs.pipe(ops.catch(handler=self._catch_error))

                return obs

            return source.pipe(ops.flat_map(_process))

        return _analyze_email

    def load_new_messages(
        self,
        limit: int = 30,
    ) -> Callable[[rx.Observable[str]], rx.Observable[gmail_types.Message]]:
        """Load new messages that are not yet in the database."""
        processed_ids: set[str] = set()

        def _update_process_ids(_: Any):
            nonlocal processed_ids
            if self.config.force_all:
                processed_ids = set()
            else:
                processed_ids = self.get_gmail_ids()

        def _load(
            trigger: rx.Observable[str],
        ) -> rx.Observable[gmail_types.Message]:
            query = self.config.gmail_query
            if query is None:
                raise ValueError("Query must be provided in the configuration.")

            pipeline = trigger.pipe(
                ops.do_action(
                    on_next=lambda _: logging.info(
                        "Starting message processing"
                    )
                ),
                ops.do_action(on_next=_update_process_ids),
                gmail_operators.fetch_ids(query=query),
                self.env.collect('mail_loading / queried gmail ids'),
            )

            def _log_item(item: gmail_types.MessageId):
                logging.debug("Found message ID: %s", item.id)
                if item.id in processed_ids:
                    logging.debug('Skipping item %s', item.id)

            def _want_to_process(item: gmail_types.MessageId) -> bool:
                return item.id not in processed_ids

            pipeline2 = pipeline.pipe(
                ops.do_action(_log_item),
                ops.filter(_want_to_process),
                self.env.collect('mail_loading / unprocessed gmail ids'),
                ops.take(limit),
            ).pipe(
                gmail_operators.download_message(),
                self.env.collect('mail_loading / downloaded gmail messages'),
                ops.catch(handler=self._catch_error),
            )
            return pipeline2

        return _load
