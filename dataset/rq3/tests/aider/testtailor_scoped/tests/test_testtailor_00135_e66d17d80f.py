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
        """Ensure the editor model line is emitted when edit_format == 'architect'."""
        # Create a Coder instance without running __init__
        coder = object.__new__(Coder)

        # Build a fake main_model with the attributes the code under test expects
        main_model = MagicMock()
        main_model.name = "main-model"
        # Make weak_model same as main to avoid extra weak-model lines
        main_model.weak_model = main_model
        main_model.get_thinking_tokens.return_value = None
        main_model.get_reasoning_effort.return_value = None
        main_model.caches_by_default = False
        main_model.info = {}

        # Editor model attributes required for the target branch
        editor_model = MagicMock()
        editor_model.name = "editor-model"
        main_model.editor_model = editor_model
        main_model.editor_edit_format = "editor-format"

        # Attach model and minimal required Coder attributes
        coder.main_model = main_model
        coder.edit_format = "architect"
        coder.add_cache_headers = False
        coder.repo = None
        coder.repo_map = None
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()
        coder.done_messages = []
        # Minimal io to satisfy access to io.multiline_mode
        coder.io = MagicMock()
        coder.io.multiline_mode = False

        # Call get_announcements and assert the editor line is present
        lines = coder.get_announcements()
        expected = f"Editor model: {main_model.editor_model.name} with {main_model.editor_edit_format} edit format"
        self.assertIn(expected, lines)
