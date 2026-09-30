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
        """Ensure get_announcements includes restored chat history when done_messages is present."""
        # Create a bare Coder instance without touching filesystem or git helpers.
        coder = Coder.__new__(Coder)

        # Minimal main_model stub
        class DummyModel:
            def __init__(self):
                self.name = "dummy-model"
                self.weak_model = self  # same weak model to avoid "Weak model" branch
                self.caches_by_default = False
                self.info = {}

            def get_thinking_tokens(self):
                return None

            def get_reasoning_effort(self):
                return None

        coder.main_model = DummyModel()
        coder.edit_format = "plain"
        coder.add_cache_headers = False
        coder.repo = None
        coder.repo_map = None

        # Minimal IO stub with multiline_mode attribute
        class DummyIO:
            def __init__(self):
                self.multiline_mode = False

        coder.io = DummyIO()

        # Basic filesystem/root settings used by get_rel_fname/get_inchat_relative_files
        coder.root = os.getcwd()
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()

        # Ensure there is a non-empty done_messages to trigger the target branch
        coder.done_messages = [{"role": "user", "content": "previous conversation"}]

        # Call the method under test
        announcements = coder.get_announcements()

        # Verify the expected announcement is present
        self.assertIn("Restored previous conversation history.", announcements)
