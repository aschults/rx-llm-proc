"""Common base for Google APIs."""

from typing import (
    Any,
)
import httplib2

from googleapiclient.http import HttpRequest
import google_auth_httplib2  # type: ignore

from . import auth


class ApiBase:
    """Base class for Google APIs."""

    def __init__(self, creds: auth.Credentials | None = None):
        """Create an instance.

        Args:
            creds: Credentials to be used for the requests.
        """
        self._creds = (
            creds or auth.CredentialsFactory.shared_instance().get_default()
        )

    def build_request(
        self, http: Any, *args: Any, **kwargs: Any
    ) -> HttpRequest:
        """Build HTTP requests for the Google API client.

        See Also:
        https://github.com/googleapis/google-api-python-client/blob/main/docs/thread_safety.md#thread-safety
        """
        new_http: Any = google_auth_httplib2.AuthorizedHttp(
            self._creds, http=httplib2.Http()
        )
        return HttpRequest(new_http, *args, **kwargs)
