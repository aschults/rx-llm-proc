"""Test the Authentication module."""

from unittest import mock
from pyfakefs import fake_filesystem_unittest  # type: ignore

from rxllmproc.core import auth


class TestCredentialsFactory(fake_filesystem_unittest.TestCase):
    """Test the credentials factory."""

    def setUp(self) -> None:
        """Set up, fake filesystem, mock the oauth function."""
        super().setUp()
        self.setUpPyfakefs()

        webflow_func_patch = mock.patch(
            ('rxllmproc.core.auth.' 'get_credentials_from_webserver_auth')
        )

        self.webflow_func_mock = webflow_func_patch.start()
        self.addCleanup(webflow_func_patch.stop)

        # Patch google.auth.default to avoid network calls
        google_auth_default_patch = mock.patch('google.auth.default')
        self.mock_google_auth_default = google_auth_default_patch.start()
        self.mock_google_auth_default.return_value = (None, None)
        self.addCleanup(google_auth_default_patch.stop)

    def test_create_simple(self):
        """Test good weather case for one credential factory."""
        instance = auth.CredentialsFactory()

        mock_credentials = mock.Mock(auth.Credentials)
        instance.factories.append(lambda _: mock_credentials)

        self.assertEqual(instance.for_label('the_label'), mock_credentials)

    def test_create_chain(self):
        """Test multiple creds factories."""
        instance = auth.CredentialsFactory()

        mock_credentials = mock.Mock(auth.Credentials)
        mock_credentials2 = mock.Mock(auth.Credentials)
        instance.factories.append(lambda _: None)
        instance.factories.append(
            lambda label: mock_credentials if label == 'the_label' else None
        )
        instance.factories.append(
            lambda label: mock_credentials2 if label == 'the_label2' else None
        )

        self.assertEqual(instance.for_label('the_label'), mock_credentials)
        self.assertEqual(instance.for_label('the_label2'), mock_credentials2)

    def test_create_cache(self):
        """Test that creds are cached (valid cred)."""
        instance = auth.CredentialsFactory()

        mock_credentials = mock.Mock(auth.Credentials)
        mock_credentials.valid = True
        mock_factory_method = mock.Mock()
        mock_factory_method.return_value = mock_credentials
        instance.factories.append(mock_factory_method)

        self.assertEqual(instance.for_label('the_label'), mock_credentials)
        self.assertEqual(1, len(mock_factory_method.call_args_list))

        self.assertEqual(instance.for_label('the_label'), mock_credentials)
        self.assertEqual(1, len(mock_factory_method.call_args_list))

    def test_create_cache_invalid(self):
        """Test that invalid cached creds are re-created."""
        instance = auth.CredentialsFactory()

        mock_credentials = mock.Mock(auth.Credentials)
        mock_credentials.valid = False
        mock_factory_method = mock.Mock()
        mock_factory_method.return_value = mock_credentials
        instance.factories.append(mock_factory_method)

        self.assertEqual(instance.for_label('the_label'), mock_credentials)
        self.assertEqual(1, len(mock_factory_method.call_args_list))

        self.assertEqual(instance.for_label('the_label'), mock_credentials)
        self.assertEqual(2, len(mock_factory_method.call_args_list))

    @mock.patch('os.environ', {})
    def test_create_default(self):
        """Test that the default OAuth factory method works."""
        instance = auth.CredentialsFactory()
        instance.add_available_credentials()
        self.fs.create_file('client_secret.json')  # type: ignore

        mock_credentials = mock.Mock(auth.Credentials)
        self.webflow_func_mock.return_value = mock_credentials

        self.assertEqual(
            instance.for_label(auth.CredentialsFactory.DEFAULT_OAUTH_LABEL),
            mock_credentials,
        )

    @mock.patch(
        'os.environ', {'RX_LLM_PROC_GOOGLE_CLIENT_SECRET_FILE': 'file.json'}
    )
    def test_create_default_with_env(self):
        """Test default OAuth, with environment override."""
        instance = auth.CredentialsFactory()
        instance.add_available_credentials()
        self.fs.create_file('file.json')  # type: ignore

        mock_credentials = mock.Mock(auth.Credentials)
        self.webflow_func_mock.return_value = mock_credentials

        self.assertEqual(
            instance.for_label(auth.CredentialsFactory.DEFAULT_OAUTH_LABEL),
            mock_credentials,
        )

    @mock.patch('os.environ', {})
    def test_create_default_missing(self):
        """Test that an exception is raised if no factories match."""
        instance = auth.CredentialsFactory()
        instance.add_available_credentials()

        mock_credentials = mock.Mock(auth.Credentials)
        self.webflow_func_mock.return_value = mock_credentials

        self.assertRaisesRegex(
            Exception,
            'not create',
            lambda: instance.for_label(
                auth.CredentialsFactory.DEFAULT_OAUTH_LABEL
            ),
        )

    def test_get_default(self):
        """Test get_default returns the default credentials."""
        instance = auth.CredentialsFactory()
        instance.default_label = auth.CredentialsFactory.DEFAULT_OAUTH_LABEL
        mock_credentials = mock.Mock(auth.Credentials)

        instance.factories.append(
            lambda label: (
                mock_credentials
                if label == auth.CredentialsFactory.DEFAULT_OAUTH_LABEL
                else None
            )
        )

        self.assertEqual(instance.get_default(), mock_credentials)

    def test_shared_instance(self):
        """Test shared_instance returns a singleton."""
        instance1 = auth.CredentialsFactory.shared_instance()
        self.assertIsInstance(instance1, auth.CredentialsFactory)
        instance2 = auth.CredentialsFactory.shared_instance()
        self.assertIs(instance1, instance2)
