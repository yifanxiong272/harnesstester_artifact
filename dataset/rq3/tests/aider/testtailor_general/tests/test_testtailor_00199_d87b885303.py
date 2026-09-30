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
        """get_announcements should include a warning for very large repos."""
        # Build a minimal Coder instance with a repo that has > 1000 files.
        coder = Coder.__new__(Coder)

        # Minimal main_model stub
        main_model = MagicMock()
        main_model.weak_model = main_model
        main_model.name = "test-model"
        main_model.get_thinking_tokens.return_value = 0
        main_model.get_reasoning_effort.return_value = None
        main_model.caches_by_default = False
        main_model.info = {}
        coder.main_model = main_model

        coder.edit_format = "plain"
        coder.add_cache_headers = False

        # Repo stub with many tracked files
        class DummyRepo:
            def get_rel_repo_dir(self):
                return "repo/dir"

            def get_tracked_files(self):
                # Return > 1000 files to trigger the large-repo warning path
                return [f"file_{i}.txt" for i in range(1500)]

        coder.repo = DummyRepo()
        coder.repo_map = None

        # Other attributes used by get_announcements
        coder.abs_read_only_fnames = set()
        coder.abs_fnames = set()
        coder.done_messages = []
        io = MagicMock()
        io.multiline_mode = False
        coder.io = io

        # Call the method under test
        lines = coder.get_announcements()

        # Verify the git repo line reports the formatted number of files
        self.assertTrue(any("with 1,500 files" in line for line in lines), lines)

        # Verify the large-repo warning lines are present
        self.assertTrue(
            any("Warning: For large repos, consider using --subtree-only and .aiderignore" in line for line in lines),
            lines,
        )
        self.assertTrue(any(line.startswith("See:") for line in lines), lines)
