"""Functionality to process Email messages."""

from typing import cast, Literal, Any
import logging
from email import message

import markdownify  # type: ignore

from rxllmproc import text_processing
from rxllmproc.text_processing import html_processing

ProcessingException = text_processing.ProcessingException


def _get_raw_email_content(msg: message.EmailMessage | None) -> str:
    """Extract and convert an email message's content/main message."""
    if msg is None:
        return ''
    try:
        body: message.MIMEPart | None = cast(
            Any, msg.get_body(('html', 'plain', 'related'))
        )
        if body is None:
            raise ProcessingException('No email body found.')
        if not body.get_payload():
            return ''
        content = body.get_content()
        return content
    except Exception as e:
        logging.exception('Cannot get body. Message: %s', msg.as_string())
        if isinstance(e, ProcessingException):
            raise e
        else:
            raise ProcessingException('Failure to get email content') from e


def get_email_content(
    msg: message.EmailMessage | None,
    output: Literal['raw', 'clean', 'md'] = 'raw',
) -> str:
    """Extract and convert an email message's content/main message."""
    content = _get_raw_email_content(msg)
    if not content or output == 'raw':
        return content

    try:
        cleaned_up = html_processing.HtmlCleaner().process(content)
        if output == 'clean':
            return cleaned_up
    except Exception:
        logging.exception('Cannot clean content. HTML: >%s<', content)
        raise

    try:
        return cast(str, markdownify.markdownify(cleaned_up))  # type: ignore
    except Exception:
        logging.exception('Markdown conversion failed. HTML: >%s<', cleaned_up)
        raise
