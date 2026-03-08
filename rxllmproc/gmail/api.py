"""GMail REST interface wrapper."""

import logging
import threading
from typing import Any, Generator
import base64

from email import message
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import dacite

from rxllmproc.gmail import types as gmail_types
from rxllmproc.core import auth, api_base
from rxllmproc.gmail import _interface


class GMailWrap(api_base.ApiBase):
    """Wrapper around GMail API."""

    def __init__(
        self,
        creds: auth.Credentials | None = None,
        service: _interface.GmailInterface | None = None,
    ):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
            service: Optionally provide service instance (mainly for testing.)
                Note: If provided, this instance is shared across threads and
                is not thread-safe.
        """
        super().__init__(creds)
        self._service_arg = service
        self._local = threading.local()
        result_dict = self._service.users().getProfile(userId='me').execute()  # type: ignore
        result = dacite.from_dict(_interface.Profile, result_dict)
        email_address = result.emailAddress
        self.me = email_address

    def get(self, msg_id: str) -> gmail_types.Message:
        """Get a message by ID."""
        logging.info('Retrieving email with id %s', msg_id)
        result_dict = (
            self._service.users()
            .messages()
            .get(
                userId=self.me,
                id=msg_id,
                format='raw',
            )
            .execute()
        )
        return dacite.from_dict(gmail_types.Message, result_dict)

    def generate_ids(
        self, q: str
    ) -> Generator[gmail_types.MessageId, None, None]:
        """Generate all message IDs matching the query."""
        try:
            page_token: str = ''
            while True:
                # Call the Gmail API
                logging.info('Retrieving email IDs for query %r', q)
                list_result_dict = (
                    self._service.users()
                    .messages()
                    .list(
                        userId=self.me,
                        q=q,
                        maxResults=500,
                        pageToken=page_token,
                    )
                    .execute()
                )
                list_result = dacite.from_dict(
                    _interface.ListMessageResponse, list_result_dict
                )
                for msg in list_result.messages:
                    if not msg.id:
                        raise ValueError('expecting message id to be set')
                    yield msg

                page_token = list_result.nextPageToken
                if not page_token:
                    break

        except HttpError:
            logging.exception('failed to query mail %s', q)
            raise

    def search(self, q: str) -> list[Any]:
        """Get message IDs for a query."""
        try:
            # Call the Gmail API
            logging.info('Retrieving emails for query %r', q)
            list_result_dict = (
                self._service.users()
                .messages()
                .list(
                    userId=self.me,
                    q=q,
                    maxResults=500,
                )
                .execute()
            )
            list_result = dacite.from_dict(
                _interface.ListMessageResponse, list_result_dict
            )
            return list_result.messages

        except HttpError:
            logging.exception('failed to query mail %s', q)
            raise

    def search_expand(self, q: str):
        """Find full messages by query."""
        list_result = self.search(q)
        for found_msg in list_result:
            yield self.get(found_msg.id)

    def send(self, msg: message.Message):
        """Send a message."""
        logging.info('sending GMail message')
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body: Any = {"raw": encoded_message}
        self._service.users().messages().send(
            userId=self.me, body=body
        ).execute()

    def send_to_me(self, subject: str, text: str):
        """Send a message user of current credentials."""
        msg = message.EmailMessage()
        msg['To'] = self.me
        msg['Subject'] = subject
        msg.set_content(text)
        self.send(msg)

    @property
    def _service(self) -> _interface.GmailInterface:
        if self._service_arg:
            return self._service_arg
        if not hasattr(self._local, 'service'):
            self._local.service = build(
                "gmail",
                "v1",
                credentials=self._creds,
                requestBuilder=self.build_request,
            )
        return self._local.service
