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
        """When a repo_map exists but its max_map_tokens == 0, the announcements
        should include the 'Repo-map: disabled because map_tokens == 0' line."""
        # Create a minimal Coder-like instance without running the full constructor.
        coder = Coder.__new__(Coder)

        # Minimal fake main_model with the attributes/methods get_announcements will access.
        MainModel = type(
            "MainModel",
            (),
            {
                "name": "mock-model",
                "weak_model": None,  # will set to self below to make weak_model is main_model
                "get_thinking_tokens": lambda self: 0,
                "get_reasoning_effort": lambda self: 0,
                "caches_by_default": False,
                "info": {},
            },
        )
        main_model = MainModel()
        main_model.weak_model = main_model

        # Attach attributes required by get_announcements
        coder.main_model = main_model
        coder.edit_format = "plain"
        coder.add_cache_headers = False
        coder.repo = None
        # repo_map exists but its max_map_tokens == 0 -> should hit target branch
        coder.repo_map = type("RM", (), {"max_map_tokens": 0})()
        # No files/read-only files in chat
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()
        coder.get_inchat_relative_files = lambda: []
        coder.get_rel_fname = lambda fname: fname
        coder.done_messages = []
        # Minimal io with multiline_mode attribute
        coder.io = type("IO", (), {"multiline_mode": False})()

        lines = Coder.get_announcements(coder)
        # Ensure the specific repo-map disabled message is present
        self.assertIn("Repo-map: disabled because map_tokens == 0", lines)
