import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.action_sampler')
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
        """If all completions fail to parse, parse_actions raises FormatError and the method logs and ultimately raises."""
        # Arrange: mock tools to raise FormatError when parse_actions is called
        mock_tools = MagicMock()
        mock_tools.parse_actions.side_effect = FormatError("cannot parse")
        mock_model = MagicMock()

        # Create AskColleagues instance and ensure a logger with a .warning method exists
        ac = AskColleagues(config=object(), model=mock_model, tools=mock_tools)
        ac._logger = MagicMock()

        completions = [{"content": "some unparseable completion"}]

        # Act & Assert: since parse_actions always fails, get_colleague_discussion should raise FormatError
        with self.assertRaises(FormatError) as cm:
            ac.get_colleague_discussion(completions)

        # Verify the exception message comes from the "no parsed completions" branch
        self.assertIn("No completions could be parsed", str(cm.exception))

        # Ensure parse_actions was called with the provided completion
        mock_tools.parse_actions.assert_called_once_with(completions[0])

        # Ensure logger.warning was called to report the parsing failure
        ac._logger.warning.assert_called_once()
        warn_args = ac._logger.warning.call_args[0]
        # First argument is the format string, second is the completion object passed
        self.assertIn("Could not parse completion", warn_args[0])
        self.assertEqual(warn_args[1], completions[0])
