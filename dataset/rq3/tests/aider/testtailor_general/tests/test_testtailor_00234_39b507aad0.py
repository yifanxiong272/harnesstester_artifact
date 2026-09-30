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
        """Ensure get_announcements emits a warning when repo_map.max_map_tokens > model.get_repo_map_tokens()*2"""
        # Create a minimal fake model with the methods/attributes used by get_announcements
        class DummyModel:
            def __init__(self):
                self.name = "dummy-model"
                # weak_model points to itself to avoid adding a separate weak-model line
                self.weak_model = self
                self.caches_by_default = False
                self.info = {}
                self.editor_model = None
                self.editor_edit_format = None

            def get_thinking_tokens(self):
                return 0

            def get_reasoning_effort(self):
                return None

            def get_repo_map_tokens(self):
                # choose a small number so max_map_tokens (x2) is predictable
                return 10

        model = DummyModel()

        # Create a Coder instance without running __init__ and set only the needed attributes
        coder = Coder.__new__(Coder)
        coder.main_model = model
        coder.edit_format = "normal"
        coder.add_cache_headers = False
        coder.repo = None

        # Create a fake repo_map with max_map_tokens greater than model.get_repo_map_tokens()*2
        fake_repo_map = MagicMock()
        fake_repo_map.max_map_tokens = model.get_repo_map_tokens() * 2 + 5  # trigger the warning
        fake_repo_map.refresh = "auto"
        coder.repo_map = fake_repo_map

        # Minimal attributes used later in get_announcements
        coder.abs_fnames = set()
        coder.abs_read_only_fnames = set()
        coder.done_messages = []
        coder.io = MagicMock()
        coder.io.multiline_mode = False

        # Call the method under test
        lines = coder.get_announcements()

        # Build expected substring using the same computation as the code under test
        max_map_tokens = model.get_repo_map_tokens() * 2
        expected_warning = f"Warning: map-tokens > {max_map_tokens} is not recommended."

        # Assert the warning appears in the announcements
        self.assertTrue(any(expected_warning in line for line in lines), f"Expected warning not found in: {lines}")
