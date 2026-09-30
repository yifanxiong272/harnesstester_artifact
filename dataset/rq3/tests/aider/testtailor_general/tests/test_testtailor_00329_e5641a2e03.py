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
        """Ensure get_commit_message skips a model when num_tokens > max_input_tokens
        and uses the next model to generate the commit message.
        """
        # Create a GitRepo instance without running __init__
        repo = GitRepo.__new__(GitRepo)

        # Minimal required attributes for get_commit_message
        repo.commit_prompt = None
        repo.io = MagicMock()
        repo.io.tool_error = MagicMock()
        repo.models = []

        # First model: will report num_tokens > max_input_tokens and should be skipped
        model1 = MagicMock()
        model1.name = "too-small-model"
        model1.system_prompt_prefix = None
        model1.token_count = MagicMock(return_value=500)
        model1.info = {"max_input_tokens": 100}
        model1.simple_send_with_retries = MagicMock(return_value=None)

        # Second model: has no max_input_tokens (or sufficiently large), will be used
        model2 = MagicMock()
        model2.name = "usable-model"
        model2.system_prompt_prefix = ""
        model2.token_count = MagicMock(return_value=50)
        model2.info = {}  # no max_input_tokens -> treated as 0 (no limit)
        # Return a message wrapped in quotes to exercise the unquoting logic
        model2.simple_send_with_retries = MagicMock(return_value='"Generated commit message"')

        repo.models = [model1, model2]

        # Call the method under test
        result = repo.get_commit_message("diffs-here", "some context", user_language="Python")

        # Verify the returned commit message (quotes stripped)
        self.assertEqual(result, "Generated commit message")

        # Verify the first model was checked and skipped (token_count called, simple_send not)
        model1.token_count.assert_called()
        model1.simple_send_with_retries.assert_not_called()

        # Verify the second model was used to generate the message
        model2.token_count.assert_called()
        model2.simple_send_with_retries.assert_called_once()

        # Ensure no error was reported to io.tool_error
        repo.io.tool_error.assert_not_called()
