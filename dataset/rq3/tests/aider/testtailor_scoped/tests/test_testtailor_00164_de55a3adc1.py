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
        """Ensure large-repo warning lines are emitted when repo has >1000 tracked files."""
        # Create a minimal fake Coder instance without running __init__
        coder = Coder.__new__(Coder)

        # Minimal fake model
        class FakeModel:
            def __init__(self, name="fake-model"):
                self.name = name
                self.weak_model = self  # same object => no "Weak model" line
                self.caches_by_default = False
                self.info = {}

            def get_thinking_tokens(self):
                return 0

            def get_reasoning_effort(self):
                return 0

        coder.main_model = FakeModel()
        coder.edit_format = "plain"
        coder.add_cache_headers = False

        # Minimal fake IO with required attribute
        coder.io = type("IO", (), {"multiline_mode": False})()

        # Repo that reports >1000 tracked files
        class FakeRepo:
            def get_rel_repo_dir(self):
                return "some/repo"

            def get_tracked_files(self):
                return ["f%d" % i for i in range(1001)]

        coder.repo = FakeRepo()

        # Other attributes used by get_announcements
        coder.abs_read_only_fnames = set()
        coder.done_messages = []
        # Provide simple implementations for used helper methods
        coder.get_inchat_relative_files = lambda: []
        coder.get_rel_fname = lambda f: f

        # Call the method under test
        lines = Coder.get_announcements(coder)

        # Assert the large-repo warning and the "See: ..." line are present
        self.assertIn(
            "Warning: For large repos, consider using --subtree-only and .aiderignore", lines
        )
        self.assertTrue(any(line.startswith("See: ") for line in lines), msg=f"lines: {lines}")
