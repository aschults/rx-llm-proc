# pyright: basic
"""Test Cemini CLI class."""

from unittest import mock
from pyfakefs import fake_filesystem_unittest


from rxllmproc.cli import rx_mail_categorizer


class TestRxMailCategorizerCli(fake_filesystem_unittest.TestCase):
    """Test the RxMailCategorizerCli class."""

    def setUp(self):
        self.setUpPyfakefs()
        # Patch PluginRegistry to avoid loading plugins during init
        with mock.patch("rxllmproc.cli.cli_base.loader.PluginRegistry"):
            self.cli = rx_mail_categorizer.RxMailCategorizerCli()

        self.cli.plugins = mock.Mock()
        self.cli.plugins.cred_store = mock.Mock()
        self.cli.cache_instance = mock.Mock()

    def test_run_missing_args(self):
        """Test check_args reports missing args."""
        self.cli.db_url = "sqlite:///:memory:"
        issues = self.cli.check_args()
        self.assertTrue(any("At least one of" in issue for issue in issues))

    def test_run_delegates_to_processing(self):
        """Test that the CLI delegates to processing classes."""
        self.fs.create_file("template.txt", contents="template content")
        self.fs.create_file("cats.txt", contents="cat content")

        self.cli.mail_config.gmail_query = "query"
        self.cli.mail_config.categorization_template = "template content"
        self.cli.model = "model"
        self.cli.db_url = "sqlite:///:memory:"
        self.cli.mail_config.categories_instructions = "cat content"
        self.cli.mail_config.action_items_instructions = "do things"
        self.cli.mail_config.context_instructions = "my context"
        self.cli.mail_config.define = {"extra": "value"}
        self.cli.mail_config.force_all = True
        self.cli.mail_config.interval = 0

        # Setup for DocsProcessing delegation
        self.cli.docs_config.todo_doc_id = "doc_id"

        with mock.patch(
            "rxllmproc.cli.rx_mail_categorizer.mail_processing.MailProcessing"
        ) as mock_mail_proc_cls, mock.patch(
            "rxllmproc.cli.rx_mail_categorizer.docs_processing.DocsProcessing"
        ) as mock_docs_proc_cls, mock.patch(
            "rxllmproc.cli.rx_mail_categorizer.app_environment.RxEnvironment"
        ) as mock_env_cls:
            # Env Mock
            mock_env = mock_env_cls.return_value

            # Processing Mocks
            mock_mail_instance = mock_mail_proc_cls.return_value
            mock_mail_instance.errors = []

            mock_docs_instance = mock_docs_proc_cls.return_value
            mock_docs_instance.errors = []

            # Run
            self.cli.run()

            # Verify MailProcessing initialized and executed
            mock_mail_proc_cls.assert_called_once()
            _, kwargs = mock_mail_proc_cls.call_args
            self.assertEqual(kwargs["config"], self.cli.mail_config)
            self.assertEqual(kwargs["env"], mock_env)
            mock_mail_instance.start_pipeline.assert_called_once_with()
            mock_mail_instance.join_pipeline.assert_called_once()

            # Verify DocsProcessing initialized and executed
            mock_docs_proc_cls.assert_called_once()
            _, kwargs = mock_docs_proc_cls.call_args
            self.assertEqual(kwargs["config"], self.cli.docs_config)
            self.assertEqual(kwargs["env"], mock_env)
            mock_docs_instance.start_pipeline.assert_called_once_with()
            mock_docs_instance.join_pipeline.assert_called_once()
