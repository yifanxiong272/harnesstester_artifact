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
    def test_summarize_failure_warns_and_continues(self):
        """If summarizer.summarize_all raises ValueError, io.tool_warning should be called."""
        # Fake coder implementation to be returned by Coder.create for the new edit_format.
        class FakeCoder:
            edit_format = "udiff"

            def __init__(self, main_model, io, **kwargs):
                # store what was passed for assertions if needed
                self.main_model = main_model
                self.io = io
                self.init_kwargs = kwargs
                # make sure attributes used elsewhere exist to avoid attribute errors
                self.original_kwargs = {}
                self.abs_fnames = set()
                self.abs_read_only_fnames = set()
                self.cur_messages = []
                self.aider_commit_hashes = set()
                self.commands = unittest.mock.MagicMock()
                self.total_cost = 0.0
                self.ignore_mentions = set()
                self.total_tokens_sent = 0
                self.total_tokens_received = 0
                self.file_watcher = None

        # Create a mocked IO so we can assert tool_warning called
        io_mock = unittest.mock.MagicMock()

        # Make a dummy from_coder object with attributes expected by Coder.create
        class DummyFromCoder:
            pass

        from_coder = DummyFromCoder()
        # different edit_format from the one we will pass to create() to trigger summarization
        from_coder.edit_format = "diff"
        # non-empty done_messages to make the condition truthy
        from_coder.done_messages = [{"role": "assistant", "content": "old message"}]
        # summarizer that will raise ValueError on summarize_all
        summarizer_mock = unittest.mock.MagicMock()
        summarizer_mock.summarize_all.side_effect = ValueError("summarize failed")
        from_coder.summarizer = summarizer_mock

        # provide other attributes used in update dict
        from_coder.original_kwargs = {"some": "value"}
        from_coder.abs_fnames = set()
        from_coder.abs_read_only_fnames = set()
        from_coder.cur_messages = []
        from_coder.aider_commit_hashes = set()
        from_coder.commands = unittest.mock.MagicMock()
        from_coder.commands.clone.return_value = "cloned_commands"
        from_coder.total_cost = 0.0
        from_coder.ignore_mentions = set()
        from_coder.total_tokens_sent = 0
        from_coder.total_tokens_received = 0
        from_coder.file_watcher = None
        from_coder.ok_to_warm_cache = True
        from_coder.main_model = unittest.mock.MagicMock()
        # Ensure create will use this io
        from_coder.io = io_mock

        # Ensure the create call will pick up our FakeCoder for edit_format "udiff"
        with unittest.mock.patch("aider.coders.__all__", new=[FakeCoder]):
            # Call Coder.create with edit_format different from from_coder.edit_format to
            # trigger summarizer.summarize_all and to hit the except ValueError branch.
            res = Coder.create(
                main_model=None,  # let create pick from from_coder.main_model
                edit_format="udiff",
                io=None,  # None so create will use from_coder.io
                from_coder=from_coder,
                summarize_from_coder=True,
            )

        # After create, from_coder.ok_to_warm_cache should be set to False
        self.assertFalse(from_coder.ok_to_warm_cache)

        # The summarizer.summarize_all should have been called and raised ValueError
        summarizer_mock.summarize_all.assert_called_once_with(from_coder.done_messages)

        # The io.tool_warning should have been called with the expected message
        io_mock.tool_warning.assert_called_once_with(
            "Chat history summarization failed, continuing with full history"
        )

        # Ensure returned object is our FakeCoder instance.
        self.assertIsInstance(res, FakeCoder)
