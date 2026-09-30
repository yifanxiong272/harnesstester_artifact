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
    def test_case_XX(self):
        """When partial_response_content is empty/whitespace, reply_completed should return early
        and not prompt or create an editor coder."""
        io = MagicMock()
        io.confirm_ask = MagicMock()

        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            from aider.coders.architect_coder import ArchitectCoder

            coder = ArchitectCoder()
            coder.io = io
            # Provide a simple main_model mock with the attributes accessed by reply_completed
            coder.main_model = MagicMock(editor_model=None, editor_edit_format="diff")
            coder.auto_accept_architect = False
            coder.verbose = False
            coder.total_cost = 0

            # whitespace-only content should trigger the early return
            coder.partial_response_content = "   "

            with patch("aider.coders.architect_coder.Coder.create") as mock_create:
                # Should return without creating an editor coder or asking confirmation
                coder.reply_completed()

                mock_create.assert_not_called()
                io.confirm_ask.assert_not_called()
