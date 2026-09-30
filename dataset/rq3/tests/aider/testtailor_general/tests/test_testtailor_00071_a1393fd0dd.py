import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repo')
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
        """Creating GitRepo with files from different repos calls tool_error and raises."""
        io = MagicMock()
        # Two filenames that should be resolved to different repos by our patched git.Repo
        fnames = ["some/path/repo1/file.txt", "other/place/repo2/another.txt"]

        # Side effect to make git.Repo(...) return different working_dir values
        def repo_side_effect(arg, search_parent_directories=True, odbt=None):
            m = MagicMock()
            arg_str = str(arg)
            if "repo1" in arg_str:
                m.working_dir = "/abs/path/to/repo1"
            elif "repo2" in arg_str:
                m.working_dir = "/abs/path/to/repo2"
            else:
                m.working_dir = "/abs/path/to/unknown"
            return m

        with patch("git.Repo", side_effect=repo_side_effect):
            with self.assertRaises(FileNotFoundError):
                GitRepo(io, fnames, None)

        io.tool_error.assert_called_once_with("Files are in different git repos.")
