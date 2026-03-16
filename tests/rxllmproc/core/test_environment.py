# pyright: reportPrivateUsage=false
"""Test the Environment class."""

import unittest
from unittest import mock
from rxllmproc.core import environment
from rxllmproc.core import auth


class TestEnvironment(unittest.TestCase):
    """Test the Environment class."""

    def setUp(self):
        self._original_instance = environment.Environment._instance
        environment.Environment._instance = None

        self.creds_patcher = mock.patch(
            'rxllmproc.core.auth.CredentialsFactory.shared_instance'
        )
        self.mock_creds_factory = self.creds_patcher.start()
        self.mock_creds_factory.return_value.get_default.return_value = (
            mock.Mock(spec=auth.Credentials)
        )

    def tearDown(self):
        self.creds_patcher.stop()

    def test_shared_not_initialized(self):
        """Test accessing shared instance without initialization."""
        with self.assertRaises(ValueError):
            environment.Environment.shared()

    def test_initialization_and_context(self):
        """Test basic initialization and context manager."""
        env = environment.Environment({})
        with env:
            self.assertIs(environment.Environment.shared(), env)

        with self.assertRaises(ValueError):
            environment.Environment.shared()

    def test_nested_environment(self):
        """Test nested environments and inheritance."""
        env1 = environment.Environment({"model_name": "model1"})
        with env1:
            self.assertEqual(
                environment.Environment.shared().model_name, "model1"
            )

            # env2 inherits from env1 (current shared)
            env2 = environment.Environment({"model_name": "model2"})
            with env2:
                self.assertIs(environment.Environment.shared(), env2)
                self.assertEqual(env2.model_name, "model2")
                # Check inheritance of creds
                self.assertEqual(env2.creds, env1.creds)

            self.assertIs(environment.Environment.shared(), env1)
            self.assertEqual(
                environment.Environment.shared().model_name, "model1"
            )

    def test_add_method(self):
        """Test the add method for creating child environments."""
        env1 = environment.Environment({"model_name": "model1"})
        with env1:
            env2 = env1.add(llm_factory_args={"temp": 0.5})
            # env2 is not active yet
            self.assertIs(environment.Environment.shared(), env1)

            with env2:
                self.assertIs(environment.Environment.shared(), env2)
                self.assertEqual(env2.model_name, "model1")  # Inherited
                self.assertEqual(env2.llm_factory_args, {"temp": 0.5})

    def test_update_method(self):
        """Test the update method for creating child environments."""
        env1 = environment.Environment(
            {"model_name": "model1", "llm_factory_args": {"temp": 0.1}}
        )

        # Update creates a new environment inheriting from env1
        # Case 1: Override a value
        env2 = env1.update({"model_name": "model2"})
        self.assertEqual(env2.model_name, "model2")
        # Inherits other values
        self.assertEqual(env2.llm_factory_args, {"temp": 0.1})

        # Case 2: Override a dictionary (replaces it, does not merge)
        env3 = env1.update({"llm_factory_args": {"top_p": 0.5}})
        self.assertEqual(env3.llm_factory_args, {"top_p": 0.5})
        # Inherits model_name
        self.assertEqual(env3.model_name, "model1")

    @mock.patch('rxllmproc.core.environment.gmail_api.GMailWrap', spec=True)
    def test_wrappers_initialization(self, gmail_mock: mock.MagicMock):
        """Test lazy initialization of wrappers."""
        env = environment.Environment({})
        with env:
            # Access gmail_wrapper
            wrapper = env.gmail_wrapper
            self.assertIsNotNone(wrapper)
            # Access again, should be same instance
            self.assertIs(env.gmail_wrapper, wrapper)

            # Access tasks_wrapper
            tasks = env.tasks_wrapper
            self.assertIsNotNone(tasks)
            self.assertIs(env.tasks_wrapper, tasks)

            # Access managed_tasks
            managed = env.managed_tasks
            self.assertIsNotNone(managed)
            self.assertIs(env.managed_tasks, managed)

        gmail_mock.assert_called_once()

    @mock.patch(
        'rxllmproc.core.environment.llm_commons.LlmModelFactory', spec=True
    )
    def test_create_model(self, llm_factory_mock: mock.MagicMock):
        """Test creating an LLM model via environment."""
        env = environment.Environment({"model_name": "test-model"})
        with env:
            env.create_model(temperature=0.7)
            llm_factory_mock.shared_instance.return_value.create.assert_called_with(
                "test-model",
                cache_instance=mock.ANY,
                functions=[],
                temperature=0.7,
            )
