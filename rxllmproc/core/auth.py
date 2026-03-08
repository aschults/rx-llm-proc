# type: ignore
"""Provide Authentication methods to access the documents."""

import logging
import os
import os.path

from typing import Sequence, Optional, Dict, Callable

from google import auth as google_auth
from google_auth_oauthlib import flow
from google.oauth2 import credentials
from google.oauth2 import service_account
from google.auth.transport import requests as goog_requests
from google.auth.exceptions import RefreshError

from google.auth.credentials import Credentials

# Default scopes to use for OAuth.
DEFAULT_SCOPES: Sequence[str] = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

SingleCredentialFactory = Callable[[str], Credentials | None]


class CredentialsFactory:
    """Class to produce credentials for Google services."""

    _shared_instance: 'CredentialsFactory| None' = None

    @classmethod
    def shared_instance(cls) -> 'CredentialsFactory':
        """Provide a shared instance."""
        if not cls._shared_instance:
            cls._shared_instance = CredentialsFactory()
            cls._shared_instance.add_available_credentials()
        return cls._shared_instance

    # Prefix for all labels that associate with service accounts.
    SERVICE_ACCOUNT_PREFIX = 'service_account:'

    # Label to use for the default OAuth credentials.
    DEFAULT_OAUTH_LABEL = 'oauth:default'

    # Label to use for Application Default Credentials.
    ADC_LABEL = 'auth:adc'

    def __init__(self) -> None:
        """Construct an instance."""
        # Keep created credentials cached so we don't repeat e.g. OAuth flows.
        self._cached: Dict[str, Credentials] | None = dict()

        # List of Credential factories, executed in order of the list.
        # First one to return credentials succeeds.
        self.factories: list[SingleCredentialFactory] = []

        # The default label to use when none is specified.
        self.default_label: str | None = None

    def for_label(
        self,
        label: Optional[str] = None,
    ) -> Credentials:
        """Fetch credentials by username."""
        if label is None:
            label = self.default_label

        creds = self._cached.get(label)
        if creds and creds.valid:
            return creds

        for factory in self.factories:
            creds = factory(label)
            if creds is not None:
                self._cached[label] = creds
                return creds
        raise Exception('could not create credentials')

    def get_default(self) -> Credentials:
        """Get the default creds."""
        return self.for_label()

    def _adc_factory(self, label: str) -> Credentials | None:
        """Obtain Application Default Credentials (ADC).

        Args:
            label: The supplied label. Honors `auth:adc` or `oauth:default`.
        """
        if label not in [self.ADC_LABEL, self.DEFAULT_OAUTH_LABEL]:
            return None

        try:
            creds, _ = google_auth.default(scopes=DEFAULT_SCOPES)
            if creds:
                logging.info('Using Application Default Credentials (ADC)')
                return creds
        except Exception as e:
            logging.debug('ADC not available or failed: %s', e)

        return None

    def _default_oauth_factory(self, label: str) -> Credentials | None:
        """Obtain the default OAuth credentials from client secrets.

        Args:
            label: The supplied label. Honors `oauth:default`.
        """
        if label != self.DEFAULT_OAUTH_LABEL:
            return None

        client_secret_file = (
            os.environ.get('RX_LLM_PROC_GOOGLE_CLIENT_SECRET_FILE')
            or 'client_secret.json'
        )

        credentials_file = (
            os.environ.get('RX_LLM_PROC_GOOGLE_CREDENTIALS_FILE')
            or 'credentials.json'
        )

        if not os.path.isfile(client_secret_file):
            logging.warning(
                'No Oauth client credentials found in %s', client_secret_file
            )
            return None

        return get_credentials_from_webserver_auth(
            client_secret_file, credentials_file
        )

    def _service_account_factory(
        self,
        label: str,
    ) -> Credentials | None:
        """Obtain credentials from a service account file.

        Args:
            label: The supplied label. Honors `service_account:.*`.
        """
        if not label.startswith(self.SERVICE_ACCOUNT_PREFIX):
            return None

        directory = (
            os.environ.get("RX_LLM_PROC_GOOGLE_SERVICE_ACCOUNTS_DIR")
            or 'service_accounts'
        )
        suffix = label[len(self.SERVICE_ACCOUNT_PREFIX) :]
        filename = f'{directory}/{suffix}.json'

        if not os.path.isfile(filename):
            logging.warning('Service Account File not found: %s', filename)
            return None

        return self.get_credentials_from_service_account(filename)

    def add_available_credentials(self) -> None:
        """Add all implemented credential factories."""
        self.factories.append(self._adc_factory)
        self.factories.append(self._default_oauth_factory)
        self.factories.append(self._service_account_factory)
        if not self.default_label:
            self.default_label = self.DEFAULT_OAUTH_LABEL

    def __str__(self) -> str:
        """Convert to string, dumping all credentials."""
        return (
            f'CredentialsStore({self.default_label}, '
            f'{self.factories}, {self._cached})'
        )


def get_credentials_from_webserver_auth(
    client_secret_file: str,
    credentials_file: str,
    scopes: Optional[Sequence[str]] = None,
) -> Credentials:
    """Return Google OAuth credentials.

    Args:
        client_secret_file: Filename for JSON file as described in
            https://github.com/googleapis/google-api-python-client/blob/main/docs/client-secrets.md
        credentials_file: Filename to file containing the JSON-serialized
            version of google.oauth2.credentials.Credentials
        scopes: The OAuth scopes used for the authentication flow.

    Returns:
        The credentials either rom credentials file or as a result of the
        OAuth flow. The returned credentials are stored in credentials_file
    """
    creds = None
    if os.path.exists(credentials_file):
        creds = credentials.Credentials.from_authorized_user_file(
            credentials_file, scopes or DEFAULT_SCOPES
        )
        if creds.valid:
            return creds
        try:
            creds.refresh(goog_requests.Request())
        except RefreshError as exception:
            logging.info('could not refresh token: %s', exception)

    if creds is None or not creds.valid:
        client_flow = flow.InstalledAppFlow.from_client_secrets_file(
            client_secret_file, scopes or DEFAULT_SCOPES
        )
        creds = client_flow.run_local_server(open_browser=False)

    if creds is None or not creds.valid:
        raise ValueError(f'Expecting valid credentials, got {creds}')

    try:
        with open(credentials_file, "w", encoding='utf-8') as filehandle:
            filehandle.write(creds.to_json())
    except OSError as exception:
        logging.warning('could not write credentials to file: %s', exception)

    return creds


def get_credentials_from_service_account(
    filename: str,
) -> service_account.Credentials:
    """Create service account credentials from a file."""
    return service_account.Credentials.from_service_account_file(filename)
