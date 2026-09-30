import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repo')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_commit_message_includes_language_instruction(self):
        """Ensure that supplying user_language adds the language instruction into the system prompt."""
        # Create a minimal dummy model that records the messages it was sent
        class DummyModel:
            def __init__(self):
                self.name = "gpt-test"
                self.system_prompt_prefix = None
                self.info = {}  # no max_input_tokens set -> treated as 0 (no limit branch)
                self.last_messages = None

            def token_count(self, messages):
                # Keep token count small so the model is always considered usable
                return 1

            def simple_send_with_retries(self, messages):
                # record the messages for inspection and return a fake commit message
                self.last_messages = messages
                return "generated commit"

        model = DummyModel()

        # Create a GitRepo instance without running __init__ to avoid git repo setup
        repo = GitRepo.__new__(GitRepo)
        # Provide a commit_prompt that includes the {language_instruction} placeholder so formatting occurs.
        repo.commit_prompt = "Please create a concise commit message.{language_instruction}\n- Keep it brief."
        repo.models = [model]
        # io is not used in this successful path, but ensure attribute exists to avoid surprises
        repo.io = MagicMock()

        # Call get_commit_message with a user_language to trigger the language_instruction branch
        result = repo.get_commit_message("diff content", "some context", user_language="Python")

        # Returned commit should be what the dummy model returned
        self.assertEqual(result, "generated commit")

        # Inspect the system message that was sent to the model and verify language instruction is present
        sent_messages = getattr(model, "last_messages", None)
        self.assertIsNotNone(sent_messages, "Model did not receive any messages")
        system_message = sent_messages[0]["content"]
        self.assertIn("- Is written in Python.", system_message)
