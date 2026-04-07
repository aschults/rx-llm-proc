"""Domain entities and types for mail processing."""

import datetime
import logging
from email import header
from email import utils
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict

import sqlalchemy
import sqlalchemy.orm

from rxllmproc.gmail import types as gmail_types
from rxllmproc.app.analysis import types as analysis_types


class MailMetadata(BaseModel):
    """Represents a single entry in the email index."""

    model_config = ConfigDict(
        from_attributes=True, extra='ignore', arbitrary_types_allowed=True
    )

    id: str = Field(description="The unique ID of the email message")
    path: Optional[str] = Field(
        default=None,
        description="File path to the stored email content",
    )
    received_date: Optional[str] = Field(
        default=None,
        description="ISO formatted date when the email was received",
    )
    subject: Optional[str] = Field(
        default=None, description="Subject line of the email"
    )
    snippet: Optional[str] = Field(
        default=None,
        description="Short snippet of the email body",
    )
    senders: Optional[str] = Field(
        default=None, description="Sender(s) of the email"
    )
    recipients: Optional[str] = Field(
        default=None, description="Recipient(s) of the email"
    )
    cc: Optional[str] = Field(default=None, description="CC recipient(s)")
    bcc: Optional[str] = Field(default=None, description="BCC recipient(s)")
    mail_data: Optional[gmail_types.Message] = Field(
        default=None,
        description="The full email message data",
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


class MailMetadataDb:
    """Database mapped class for MailMetadata."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)

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
                "mail_data": sqlalchemy.orm.relationship(
                    gmail_types.MessageDb,
                    uselist=False,
                    backref="mail_metadata",
                    cascade="all",
                ),
            },
        )


class MailSource(analysis_types.Source):
    """Email source data for analysis."""

    mail_metadata: MailMetadata = Field(
        default_factory=lambda: MailMetadata(id=""),
        description="Metadata of the email",
    )


class MailSourceDb(analysis_types.SourceDb):
    """Database mapped class for MailSource."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize attributes from kwargs."""
        super().__init__(**kwargs)

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
            inherits=analysis_types.SourceDb,
            polymorphic_identity="mail_source",
            properties={
                'mail_metadata': sqlalchemy.orm.relationship(
                    MailMetadataDb,
                    uselist=False,
                    backref='mail_source',
                    cascade="all",
                ),
            },
        )


class MailPipelineConfig(BaseModel):
    """Configuration for processing."""

    model_config = ConfigDict(extra='ignore')

    gmail_query: Optional[str] = None
    force_all: bool = False
    categorization_template: Optional[str] = Field(
        default=None, json_schema_extra={'expand_file': True}
    )
    categories_instructions: Optional[str] = Field(
        default=None, json_schema_extra={'expand_file': True}
    )
    action_items_instructions: Optional[str] = Field(
        default=None,
        json_schema_extra={'expand_file': True},
    )
    context_instructions: Optional[str] = Field(
        default=None, json_schema_extra={'expand_file': True}
    )
    define: Optional[dict[str, Any]] = Field(
        default=None,
        json_schema_extra={
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


class MailConfig(MailPipelineConfig):
    """Configuration for execution."""

    model_config = ConfigDict(extra='ignore')

    interval: float = 60
