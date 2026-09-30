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
        """get_announcements includes editor model line when edit_format == 'architect'"""
        # Create a minimal fake model with the needed attributes/methods
        class FakeEditor:
            def __init__(self):
                self.name = "fake-editor-model"

        class FakeModel:
            def __init__(self):
                self.name = "fake-main-model"
                # weak_model can be same as main model for this test
                self.weak_model = self
                self.caches_by_default = False
                self.info = {}
                self.editor_model = FakeEditor()
                self.editor_edit_format = "fake-edit-format"

            def get_thinking_tokens(self):
                return 0

            def get_reasoning_effort(self):
                return None

            def get_repo_map_tokens(self):
                return 0

        # Build a Coder instance without running the full __init__
        coder = object.__new__(Coder)
        coder.main_model = FakeModel()
        coder.edit_format = "architect"  # trigger the editor-model branch
        coder.add_cache_headers = False
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()
        coder.repo = None
        coder.repo_map = None
        coder.done_messages = []
        # Minimal io object with multiline_mode attribute (used at end of get_announcements)
        coder.io = type("IO", (), {"multiline_mode": False})()

        # Call the method under test
        lines = coder.get_announcements()

        # Expect the editor model line to be present with correct formatting
        expected = f"Editor model: {coder.main_model.editor_model.name} with {coder.main_model.editor_edit_format} edit format"
        self.assertTrue(any(expected == line for line in lines), f"Expected line not found in announcements: {expected}")
