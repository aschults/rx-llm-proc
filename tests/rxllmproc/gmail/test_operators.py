"""Test the GMail reactive operators."""

from typing import Iterator
import unittest
from unittest import mock
import reactivex as rx

from rxllmproc.gmail import operators as gmail_operators
from rxllmproc.core import environment
from rxllmproc.gmail import api as gmail_wrapper
from rxllmproc.gmail import types as gmail_types


class TestGmailOperators(unittest.TestCase):
    """Test the GMail reactive operators."""

    def setUp(self):
        self.creds_patcher = mock.patch(
            'rxllmproc.core.auth.CredentialsFactory.shared_instance'
        )
        self.creds_patcher.start()
        self.env = environment.Environment()
        self.env.__enter__()

    def tearDown(self):
        self.env.__exit__(None, None, None)
        self.creds_patcher.stop()

    def test_fetch_messages(self):
        """Test fetching messages triggered by an observable."""
        wrapper = mock.Mock(spec=gmail_wrapper.GMailWrap)
        msg1 = gmail_types.Message(id='1', snippet='s1')
        msg2 = gmail_types.Message(id='2', snippet='s2')

        # Mock search_expand to return an iterator
        wrapper.search_expand.return_value = iter([msg1, msg2])

        results: list[gmail_types.Message | Exception] = []

        # Create a source that emits one item (the trigger)
        source = rx.of('trigger')

        # Apply the operator
        source.pipe(
            gmail_operators.fetch_messages("label:INBOX", wrapper=wrapper)
        ).subscribe(
            on_next=results.append, on_error=lambda e: results.append(e)
        )

        self.assertEqual(results, [msg1, msg2])
        wrapper.search_expand.assert_called_once_with("label:INBOX")

    def test_fetch_messages_multiple_triggers(self):
        """Test fetching messages with multiple triggers."""
        wrapper = mock.Mock(spec=gmail_wrapper.GMailWrap)
        msg1 = gmail_types.Message(id='1', snippet='s1')

        # Mock search_expand to return a new iterator each time
        def _side_effect(q: str) -> Iterator[gmail_types.Message]:
            return iter([msg1])

        wrapper.search_expand.side_effect = _side_effect

        results: list[gmail_types.Message] = []

        # Create a source that emits two items
        source = rx.from_iterable(['trigger1', 'trigger2'])

        source.pipe(
            gmail_operators.fetch_messages("query", wrapper=wrapper)
        ).subscribe(results.append)

        self.assertEqual(results, [msg1, msg1])
        self.assertEqual(wrapper.search_expand.call_count, 2)

    @mock.patch('rxllmproc.gmail.api.GMailWrap')
    def test_fetch_messages_default_wrapper(
        self, mock_wrapper_cls: mock.MagicMock
    ):
        """Test fetching messages creating a default wrapper."""
        wrapper_instance = mock_wrapper_cls.return_value
        wrapper_instance.search_expand.return_value = iter([])

        source = rx.of('trigger')
        source.pipe(gmail_operators.fetch_messages("query")).subscribe()

        mock_wrapper_cls.assert_called_once()
        wrapper_instance.search_expand.assert_called_with("query")

    def test_fetch_ids(self):
        """Test fetching message IDs triggered by an observable."""
        wrapper = mock.Mock(spec=gmail_wrapper.GMailWrap)
        id1 = gmail_types.MessageId(id='1', threadId='t1')
        id2 = gmail_types.MessageId(id='2', threadId='t2')

        # Mock search to return an iterator
        wrapper.search.return_value = iter([id1, id2])

        results: list[gmail_types.MessageId | Exception] = []

        # Create a source that emits one item (the trigger)
        source = rx.of('trigger')

        # Apply the operator
        source.pipe(
            gmail_operators.fetch_ids("label:INBOX", wrapper=wrapper)
        ).subscribe(
            on_next=results.append, on_error=lambda e: results.append(e)
        )

        self.assertEqual(results, [id1, id2])
        wrapper.search.assert_called_once_with("label:INBOX")

    @mock.patch('rxllmproc.gmail.api.GMailWrap')
    def test_fetch_ids_default_wrapper(self, mock_wrapper_cls: mock.MagicMock):
        """Test fetching message IDs creating a default wrapper."""
        wrapper_instance: mock.MagicMock = mock_wrapper_cls.return_value
        wrapper_instance.search.return_value = iter([])

        source = rx.of('trigger')
        source.pipe(gmail_operators.fetch_ids("query")).subscribe()

        mock_wrapper_cls.assert_called_once()
        wrapper_instance.search.assert_called_with("query")

    def test_download_message(self):
        """Test downloading a message by ID."""
        wrapper = mock.Mock(spec=gmail_wrapper.GMailWrap)
        msg_id = gmail_types.MessageId(id='123', threadId='t1')
        expected_msg = gmail_types.Message(id='123', snippet='content')

        wrapper.get.return_value = expected_msg

        results: list[gmail_types.Message] = []
        source = rx.of(msg_id)

        source.pipe(
            gmail_operators.download_message(wrapper=wrapper)
        ).subscribe(results.append)

        self.assertEqual(results, [expected_msg])
        wrapper.get.assert_called_once_with('123')

    def test_download_message_str_id(self):
        """Test downloading a message by string ID."""
        wrapper = mock.Mock(spec=gmail_wrapper.GMailWrap)
        msg_id = '123'
        expected_msg = gmail_types.Message(id='123', snippet='content')

        wrapper.get.return_value = expected_msg

        results: list[gmail_types.Message] = []
        source = rx.of(msg_id)

        source.pipe(
            gmail_operators.download_message(wrapper=wrapper)
        ).subscribe(results.append)

        self.assertEqual(results, [expected_msg])
        wrapper.get.assert_called_once_with('123')

    @mock.patch('rxllmproc.gmail.api.GMailWrap')
    def test_download_message_default_wrapper(
        self, mock_wrapper_cls: mock.MagicMock
    ):
        """Test downloading message using default wrapper."""
        wrapper_instance = mock_wrapper_cls.return_value
        source = rx.of('123')
        source.pipe(gmail_operators.download_message()).subscribe()
        wrapper_instance.get.assert_called_with('123')
