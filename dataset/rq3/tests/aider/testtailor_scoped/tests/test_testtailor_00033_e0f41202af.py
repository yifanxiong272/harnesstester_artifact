import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.architect_coder')
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
    def test_architect_reply_completed_returns_on_empty_content(self):
        """If partial_response_content is empty/whitespace, reply_completed should return early
        and not attempt to create or run an editor coder or ask for confirmation."""
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            from aider.coders.architect_coder import ArchitectCoder

            coder = ArchitectCoder()
            # whitespace content should trigger the early return (not content.strip() == True)
            coder.partial_response_content = "   "
            # provide a mocked io to ensure confirm_ask would be available if called
            coder.io = MagicMock()
            coder.io.confirm_ask = MagicMock(return_value=True)

            with patch("aider.coders.architect_coder.Coder.create") as mock_create:
                # Call the method under test
                coder.reply_completed()

                # Since content is only whitespace, Coder.create should never be called
                mock_create.assert_not_called()

                # confirm_ask should also not be invoked because the function returns early
                coder.io.confirm_ask.assert_not_called()
