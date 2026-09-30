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
        """Ensure editor_coder.show_announcements() is called when verbose is True"""
        # Use a simple mock IO so we don't depend on other helpers that might not be available
        io = MagicMock()
        io.confirm_ask = MagicMock(return_value=True)

        # Patch the AskCoder.__init__ so we can construct ArchitectCoder without full init
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            from aider.coders.architect_coder import ArchitectCoder

            coder = ArchitectCoder()
            coder.io = io

            # Provide a minimal main_model object with required attributes.
            main_model = MagicMock()
            main_model.editor_model = None  # force code path to use main_model itself
            main_model.editor_edit_format = "diff"
            coder.main_model = main_model

            coder.auto_accept_architect = True  # auto-accept so confirm_ask is not invoked
            coder.verbose = True  # must be True to trigger show_announcements()
            coder.total_cost = 0
            coder.cur_messages = []
            coder.done_messages = []
            coder.summarizer = MagicMock()
            coder.summarizer.too_big.return_value = False

            # Mock the editor coder created by Coder.create
            mock_editor = MagicMock()
            mock_editor.run = MagicMock()
            mock_editor.show_announcements = MagicMock()
            # Ensure attributes assignment in reply_completed works
            mock_editor.cur_messages = []
            mock_editor.done_messages = []
            mock_editor.total_cost = 123
            mock_editor.aider_commit_hashes = ["abc"]

            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                # Provide a non-empty partial response so reply_completed proceeds
                coder.partial_response_content = "Apply these changes to files"

                # Call the method under test
                coder.reply_completed()

                # Because auto_accept_architect is True, confirm_ask should not be called
                io.confirm_ask.assert_not_called()

                # With verbose True, the editor coder's show_announcements should be invoked
                mock_editor.show_announcements.assert_called_once()

                # And the editor coder should have been run with the content and preproc=False
                mock_editor.run.assert_called_once_with(with_message=coder.partial_response_content, preproc=False)
