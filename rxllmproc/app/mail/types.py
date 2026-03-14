"""Domain entities and types for mail processing."""

import dataclasses
import datetime
import logging
from email import header
from email import utils
from typing import Any

import sqlalchemy
import sqlalchemy.orm

from rxllmproc.gmail import types as gmail_types
from rxllmproc.app.analysis import types as analysis_types


@dataclasses.dataclass
class MailMetadata:
    """Represents a single entry in the email index."""

    id: str = dataclasses.field(
        metadata={"description": "The unique ID of the email message"},
    )
    path: str | None = dataclasses.field(
        default=None,
        metadata={"description": "File path to the stored email content"},
    )
    received_date: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "ISO formatted date when the email was received"
        },
    )
    subject: str | None = dataclasses.field(
        default=None, metadata={"description": "Subject line of the email"}
    )
    snippet: str | None = dataclasses.field(
        default=None,
        metadata={"description": "Short snippet of the email body"},
    )
    senders: str | None = dataclasses.field(
        default=None, metadata={"description": "Sender(s) of the email"}
    )
    recipients: str | None = dataclasses.field(
        default=None, metadata={"description": "Recipient(s) of the email"}
    )
    cc: str | None = dataclasses.field(
        default=None, metadata={"description": "CC recipient(s)"}
    )
    bcc: str | None = dataclasses.field(
        default=None, metadata={"description": "BCC recipient(s)"}
    )
    mail_data: gmail_types.Message | None = dataclasses.field(
        default=None,
        metadata={"description": "The full email message data"},
    )

    @staticmethod
    def _decode_email_header(header_str: str) -> str | None:
        """Decodes email headers to a readable string."""
        if not header_str:
            return None
        decoded_parts: list[str] = []
        for part, charset in header.decode_header(header_str):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or "utf-8", "ignore"))
            else:
                decoded_parts.append(str(part))
        return "".join(decoded_parts)

    @property
    def url(self) -> str:
        """Constructs the Gmail URL for the message."""
        return f"https://mail.google.com/mail/u/0/#inbox/{self.id}"

    @classmethod
    def from_msg(
        cls, gmail_msg: gmail_types.Message, path: str | None = None
    ) -> "MailMetadata":
        """Creates an MailMetadata from a Message object."""
        if not gmail_msg.id:
            raise ValueError("Message has no ID, cannot create index entry.")

        msg = gmail_msg.parsed_msg
        date_str = cls._decode_email_header(msg.get("Date", ""))
        iso_date = date_str
        try:
            dt = utils.parsedate_to_datetime(date_str)
            if dt:
                if dt.tzinfo:
                    dt = dt.astimezone(datetime.timezone.utc)
                iso_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            logging.exception(f"Could not parse date string: {date_str}")
            raise

        return cls(
            id=gmail_msg.id,
            path=path or f"{gmail_msg.id}.msg",
            subject=cls._decode_email_header(msg.get("Subject", "")),
            received_date=iso_date,
            snippet=gmail_msg.snippet,
            senders=cls._decode_email_header(msg.get("From", "")),
            recipients=cls._decode_email_header(msg.get("To", "")),
            cc=cls._decode_email_header(msg.get("Cc", "")),
            bcc=cls._decode_email_header(msg.get("Bcc", "")),
            mail_data=gmail_msg,
        )

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        id_column = sqlalchemy.Column(
            "id",
            sqlalchemy.String,
            primary_key=True,
        )
        table = sqlalchemy.Table(
            "mail_metadata",
            registry.metadata,
            id_column,
            sqlalchemy.Column("path", sqlalchemy.String),
            sqlalchemy.Column("received_date", sqlalchemy.String),
            sqlalchemy.Column("subject", sqlalchemy.String),
            sqlalchemy.Column("snippet", sqlalchemy.String),
            sqlalchemy.Column("senders", sqlalchemy.String),
            sqlalchemy.Column("recipients", sqlalchemy.String),
            sqlalchemy.Column("cc", sqlalchemy.String),
            sqlalchemy.Column("bcc", sqlalchemy.String),
            sqlalchemy.Column(
                "mail_data_id",
                sqlalchemy.String,
                sqlalchemy.ForeignKey("gmail_message.id"),
            ),
        )
        registry.map_imperatively(
            cls,
            table,
            properties={
                "id": id_column,
                "mail_data": sqlalchemy.orm.relationship(
                    gmail_types.Message,
                    uselist=False,
                    backref="mail_metadata",
                    cascade="all",
                ),
            },
        )


@dataclasses.dataclass(kw_only=True)
class MailSource(analysis_types.Source):
    """Email source data for analysis."""

    mail_metadata: MailMetadata = dataclasses.field(
        metadata={"description": "Metadata of the email"}
    )

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        table = sqlalchemy.Table(
            "mail_source",
            registry.metadata,
            sqlalchemy.Column(
                "id",
                sqlalchemy.String,
                sqlalchemy.ForeignKey("source.id"),
                primary_key=True,
            ),
            sqlalchemy.Column(
                "mail_metadata_id",
                sqlalchemy.String,
                sqlalchemy.ForeignKey("mail_metadata.id"),
            ),
        )
        registry.map_imperatively(
            cls,
            table,
            inherits=analysis_types.Source,
            polymorphic_identity="mail_source",
            properties={
                'mail_metadata': sqlalchemy.orm.relationship(
                    "MailMetadata",
                    uselist=False,
                    backref='mail_source',
                    cascade="all",
                ),
            },
        )


@dataclasses.dataclass
class MailPipelineConfig:
    """Configuration for processing."""

    gmail_query: str | None = None
    force_all: bool = False
    categorization_template: str | None = dataclasses.field(
        default=None, metadata={'expand_file': True}
    )
    categories_instructions: str | None = dataclasses.field(
        default=None, metadata={'expand_file': True}
    )
    action_items_instructions: str | None = dataclasses.field(
        default=None,
        metadata={'expand_file': True},
    )
    context_instructions: str | None = dataclasses.field(
        default=None, metadata={'expand_file': True}
    )
    define: dict[str, Any] | None = dataclasses.field(
        default=None,
        metadata={
            'expand_dict': True,
            'expand_values': 'expand_args_typed',
        },
    )

    @property
    def template_parameters(self) -> dict[str, Any]:
        """Get template parameters."""
        params = (self.define or {}).copy()
        if self.categories_instructions:
            params["categories_instructions"] = self.categories_instructions
        if self.action_items_instructions:
            params["action_items_instructions"] = self.action_items_instructions
        if self.context_instructions:
            params["context_instructions"] = self.context_instructions
        return params

    @property
    def template_content(self) -> str:
        """Get template content."""
        return self.categorization_template or ""


@dataclasses.dataclass
class MailConfig(MailPipelineConfig):
    """Configuration for execution."""

    interval: float = 60
