import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.base_coder')
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
        """Ensure that when summarization raises ValueError, we warn and continue."""
        # Create a mock io that captures tool_warning calls
        io = unittest.mock.Mock()
        io.tool_warning = unittest.mock.Mock()

        # Dummy summarizer that raises ValueError when summarize_all is called
        class DummySummarizer:
            def summarize_all(self, messages):
                raise ValueError("summarize failed")

        # Dummy commands with a clone method (used by Coder.create)
        class DummyCommands:
            def clone(self):
                return DummyCommands()

        # Minimal from_coder object with the attributes Coder.create expects
        class DummyFromCoder:
            pass

        from_coder = DummyFromCoder()
        from_coder.main_model = object()  # simple placeholder
        from_coder.edit_format = "orig_format"
        from_coder.original_kwargs = {}
        # non-empty -> triggers summarization attempt
        from_coder.done_messages = [{"role": "assistant", "content": "history"}]
        from_coder.cur_messages = []
        from_coder.aider_commit_hashes = set()
        from_coder.commands = DummyCommands()
        from_coder.total_cost = 0.0
        from_coder.ignore_mentions = set()
        from_coder.total_tokens_sent = 0
        from_coder.total_tokens_received = 0
        from_coder.file_watcher = None
        from_coder.abs_fnames = set()
        from_coder.abs_read_only_fnames = set()
        from_coder.summarizer = DummySummarizer()
        from_coder.ok_to_warm_cache = False

        # Call create with an explicit edit_format different from from_coder.edit_format to trigger
        # the summarization attempt. It will ultimately raise UnknownEditFormat (or similar)
        # because no coder matches "new_format"; our goal is to ensure the ValueError path is hit
        # and io.tool_warning was invoked.
        with self.assertRaises(Exception):
            Coder.create(main_model=None, edit_format="new_format", io=io, from_coder=from_coder)

        io.tool_warning.assert_called_once_with(
            "Chat history summarization failed, continuing with full history"
        )
