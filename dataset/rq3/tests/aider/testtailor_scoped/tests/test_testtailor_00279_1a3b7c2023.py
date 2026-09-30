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
        """Ensure get_announcements includes restored history when done_messages is present."""
        # Create a minimal dummy model with the attributes used by get_announcements
        class DummyModel:
            def __init__(self, name):
                self.name = name
                self.weak_model = self  # make weak_model the same to exercise the "Model" prefix path
                self.caches_by_default = False
                self.info = {}

            def get_thinking_tokens(self):
                return None

            def get_reasoning_effort(self):
                return None

        # Minimal IO object with the attribute used by get_announcements
        io = type("IO", (), {"multiline_mode": False})()

        # Create a Coder instance without running __init__ to avoid heavy setup;
        # populate only the attributes needed by get_announcements.
        coder = object.__new__(Coder)
        coder.main_model = DummyModel("gpt-test-model")
        coder.edit_format = "plain"
        coder.add_cache_headers = False
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()
        coder.repo = None
        coder.repo_map = None
        coder.io = io
        # The condition we want to trigger:
        coder.done_messages = ["previous conversation"]

        lines = coder.get_announcements()
        self.assertIn("Restored previous conversation history.", lines)
