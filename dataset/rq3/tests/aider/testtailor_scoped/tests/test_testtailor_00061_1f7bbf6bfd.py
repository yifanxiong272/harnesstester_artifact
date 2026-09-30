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
        """Ensure GitRepo raises FileNotFoundError and logs error when files are in different repos."""
        # Prepare a simple IO mock that records tool_error calls
        io = MagicMock()
        io.tool_error = MagicMock()

        # side effect for git.Repo to return different working_dir values based on input path
        def repo_side_effect(path_arg, search_parent_directories=True, **kwargs):
            p = str(path_arg)
            mock_repo = MagicMock()
            if "repo1" in p:
                mock_repo.working_dir = "/fake/path/repo1"
                return mock_repo
            if "repo2" in p:
                mock_repo.working_dir = "/fake/path/repo2"
                return mock_repo
            # For any other path, simulate not a git repo by raising an error
            raise Exception("not a git repo")

        with patch("git.Repo", side_effect=repo_side_effect):
            fnames = ["/some/dir/repo1/file.txt", "/other/dir/repo2/other.txt"]
            with self.assertRaises(FileNotFoundError):
                GitRepo(io, fnames=fnames, git_dname=None, models=[])
            io.tool_error.assert_called_once_with("Files are in different git repos.")
