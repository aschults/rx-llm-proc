"""GMail classes (from REST interface) used in steps."""

import dataclasses
import base64
import re
import logging
from email import message, parser, policy
import sqlalchemy
import sqlalchemy.orm
from rxllmproc.text_processing import email_processing


@dataclasses.dataclass
class Header:
    """Single email header."""

    name: str
    value: str

    def is_name(self, name: str) -> bool:
        """Check if name matches, case insensitive."""
        return self.name.lower() == name.lower()

    @classmethod
    def get_named_header(cls, headers: "list[Header]", name: str) -> str | None:
        """Retreive a header value by name."""
        for header in headers:
            if header.is_name(name):
                return header.value
        return None


@dataclasses.dataclass
class MessagePartBody:
    """Body of an email part."""

    attachmentId: str | None = None
    size: int | None = None
    data: str | None = None


@dataclasses.dataclass
class MessagePart:
    """Part of a message."""

    partId: str | None = None
    mimeType: str | None = None
    filename: str | None = None
    headers: list[Header] = dataclasses.field(default_factory=lambda: [])
    body: MessagePartBody = dataclasses.field(default_factory=MessagePartBody)
    parts: "list[MessagePart]" = dataclasses.field(default_factory=lambda: [])

    @property
    def subject(self) -> str:
        """Get the subject of the email."""
        return Header.get_named_header(self.headers, "subject") or ""

    @subject.setter
    def subject(self, subject: str):
        for header in self.headers:
            if header.is_name("subject"):
                header.value = subject
                return

        self.headers.append(Header("Subject", subject))

    @property
    def sender(self) -> str:
        """Get the sender of the email."""
        return Header.get_named_header(self.headers, "from") or ""

    @property
    def main_message(self) -> tuple[str, str] | None:
        """Extract the main message."""
        mime_type = (self.mimeType or "").split(";")[0]
        if mime_type in ("text/plain", "text/html"):
            if self.body.attachmentId is not None:
                raise Exception(
                    f"unexpected attachment id {self.body.attachmentId}"
                )
            if not self.body.data:
                logging.warning("empty body")
            else:
                return (
                    mime_type,
                    base64.urlsafe_b64decode(self.body.data).decode(),
                )

        if not mime_type.startswith("multipart/"):
            return None

        plain_result = None
        for p in self.parts:
            msg = p.main_message
            if msg is None:
                continue

            if msg[0] == "text/html":
                return msg
            if msg[0] == "text/plain":
                plain_result = msg

        if plain_result:
            return plain_result

        return None


@dataclasses.dataclass
class MessageId:
    """The IDs (message, thread) of a GMail message."""

    id: str
    threadId: str | None = None


@dataclasses.dataclass
class Message:
    """Represents one email message."""

    id: str | None = None
    threadId: str | None = None
    labelIds: list[str] = dataclasses.field(default_factory=lambda: [])
    snippet: str | None = None
    historyId: str | None = None
    internalDate: str | None = None
    payload: MessagePart | None = None
    sizeEstimate: int | None = None
    raw: str | None = None

    def __post_init__(self):
        """Post-initialization to set up private attributes."""
        self._parsed_msg: message.Message | None = None

    @property
    def parsed_msg(self) -> message.EmailMessage:
        """Lazily parse the raw message body."""
        if self._parsed_msg is None:
            if not self.raw:
                raise ValueError("Message has no raw content to parse.")
            decoded_msg = base64.urlsafe_b64decode(self.raw.encode())
            self._parsed_msg = parser.BytesParser(
                policy=policy.default
            ).parsebytes(decoded_msg)
        if not isinstance(self._parsed_msg, message.EmailMessage):
            raise TypeError(
                f"Expected EmailMessage, got {type(self._parsed_msg)}"
            )
        return self._parsed_msg

    @property
    def main_message(self) -> tuple[str, str] | None:
        """Extract the main message, including multipart."""
        if self.payload:
            return self.payload.main_message

        body = self.parsed_msg.get_body(preferencelist=("html", "plain"))
        if body:
            return (body.get_content_type(), body.get_content())
        return None

    @property
    def markdown_body(self) -> str:
        """Get the email body as markdown."""
        return email_processing.get_email_content(self.parsed_msg, 'md')

    @property
    def subject(self) -> str:
        """Get the email subject."""
        if self.payload:
            return self.payload.subject
        return str(self.parsed_msg.get("subject", ""))

    @property
    def sender(self) -> str:
        """Get the email sender."""
        if self.payload:
            return self.payload.sender
        return str(self.parsed_msg.get("from", ""))

    @property
    def msg_id(self) -> str:
        """Get the Email RFC ID."""
        if self.payload:
            value = Header.get_named_header(self.payload.headers, "message-id")
        else:
            value = str(self.parsed_msg.get("message-id", ""))
        if not value:
            raise ValueError("expected message-id")
        match = re.match(r"^<(.*)>$", value)
        if match:
            return match.group(1)
        return value

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry):
        table = sqlalchemy.Table(
            "gmail_message",
            registry.metadata,
            sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("threadId", sqlalchemy.String),
            sqlalchemy.Column("snippet", sqlalchemy.String),
            sqlalchemy.Column("historyId", sqlalchemy.String),
            sqlalchemy.Column("internalDate", sqlalchemy.String),
            sqlalchemy.Column("sizeEstimate", sqlalchemy.Integer),
            sqlalchemy.Column("raw", sqlalchemy.String),
        )
        registry.map_imperatively(cls, table)
