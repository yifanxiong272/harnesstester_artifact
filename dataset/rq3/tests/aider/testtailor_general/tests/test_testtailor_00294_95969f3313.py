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
    def test_case_XX(self):
        """Verify that providing user_language inserts the language instruction into the system prompt."""
        # Capture calls for inspection
        calls = []

        class DummyModel:
            def __init__(self):
                self.name = "dummy-model"
                self.system_prompt_prefix = None
                self.info = {}

            def token_count(self, messages):
                # return a small token count so max_tokens checks pass
                calls.append(("token_count", messages))
                return 0

            def simple_send_with_retries(self, messages):
                # record the messages and return a generated commit message
                calls.append(("send", messages))
                return "generated commit"

        model = DummyModel()

        # Instantiate GitRepo without running __init__ to avoid filesystem/git requirements
        repo = GitRepo.__new__(GitRepo)
        # Provide a commit_prompt that includes the language_instruction placeholder used by the code
        repo.commit_prompt = "System instructions.{language_instruction}\nEnd of prompt."
        repo.models = [model]

        # Call the method under test
        result = GitRepo.get_commit_message(repo, "dummy diff", "dummy context", user_language="Python")

        # Verify returned commit message
        self.assertEqual(result, "generated commit")

        # Ensure the model send method was invoked
        send_calls = [c for c in calls if c[0] == "send"]
        self.assertTrue(send_calls, "Expected the model's send method to be called")

        # Inspect the system prompt passed to the model and confirm language instruction present
        messages_sent = send_calls[0][1]
        system_msg = messages_sent[0]["content"]
        self.assertIn("- Is written in Python.", system_msg)
