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
        """get_announcements should include read-only files from abs_read_only_fnames"""
        # Obtain Coder class without a top-level import statement
        Coder = __import__("aider.coders", fromlist=["Coder"]).Coder

        # Create a bare Coder instance without running its __init__
        coder = object.__new__(Coder)

        # Minimal dummy main_model that satisfies attributes/methods used by get_announcements
        class DummyModel:
            def __init__(self):
                self.name = "dummy-model"
                self.weak_model = self  # make weak_model identical to main_model
                self.caches_by_default = False
                self.info = {}

            def get_thinking_tokens(self):
                return 0

            def get_reasoning_effort(self):
                return 0

        coder.main_model = DummyModel()
        coder.edit_format = "plain"
        coder.add_cache_headers = False

        # Provide a read-only filename (absolute path string). get_announcements will call
        # coder.get_rel_fname for each abs_read_only_fnames entry; provide a simple resolver.
        abs_path = "/abs/path/read_only.txt"
        coder.abs_read_only_fnames = {abs_path}

        # Simple implementations for methods/attributes used by get_announcements
        coder.get_rel_fname = lambda fname: "read_only.txt"
        coder.get_inchat_relative_files = lambda: []
        coder.done_messages = []
        coder.io = type("IO", (), {"multiline_mode": False})()
        coder.repo = None
        coder.repo_map = None

        # Call the method under test
        announcements = Coder.get_announcements(coder)

        # Verify the read-only file announcement is present
        expected = "Added read_only.txt to the chat (read-only)."
        self.assertIn(expected, announcements)
