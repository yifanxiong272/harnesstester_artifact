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
        """Repo-map present but disabled when map_tokens == 0 should be announced."""
        # Create a Coder instance without running __init__
        coder = Coder.__new__(Coder)

        # Minimal dummy model with the attributes/methods accessed by get_announcements
        class DummyModel:
            def __init__(self):
                self.weak_model = self  # make weak_model the same so branch uses "Model"
                self.name = "dummy-model"
                self.info = {}  # used with .get(...)
                self.caches_by_default = False
                self.extra_params = {}
                self.streaming = False
                self.edit_format = None

            def get_thinking_tokens(self):
                return 0

            def get_reasoning_effort(self):
                return None

        dummy_model = DummyModel()

        # Attach required attributes/methods on the fake coder
        coder.main_model = dummy_model
        coder.edit_format = None
        coder.add_cache_headers = False
        coder.io = MagicMock()
        coder.io.multiline_mode = False

        coder.repo = None  # Ensure repo branch takes the "none" path (not required for target)
        # Provide a truthy repo_map but with max_map_tokens == 0 to hit the target branch
        coder.repo_map = MagicMock()
        coder.repo_map.max_map_tokens = 0

        # Methods and collections used later in get_announcements
        coder.get_inchat_relative_files = lambda: []
        coder.abs_read_only_fnames = set()
        coder.get_rel_fname = lambda fname: fname
        coder.done_messages = []

        # Call the method and assert the expected line is present
        announcements = Coder.get_announcements(coder)
        self.assertIn("Repo-map: disabled because map_tokens == 0", announcements)
