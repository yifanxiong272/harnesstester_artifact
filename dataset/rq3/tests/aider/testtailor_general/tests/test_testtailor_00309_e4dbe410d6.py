import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.main')
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
        """When cwd equals the user's home directory and no git_root is provided,
        setup_git should warn the user and return without creating a repo."""
        orig_cwd = os.getcwd()
        # Create a unique fake home directory inside the current working directory
        uuid = __import__("uuid")
        fake_home = Path(orig_cwd) / ("fake_home_" + uuid.uuid4().hex)
        fake_home.mkdir()
        try:
            os.chdir(str(fake_home))
            # Make Path.home() return our fake home so cwd == Path.home()
            with patch("pathlib.Path.home", return_value=fake_home):
                mock_io = MagicMock()
                res = setup_git(None, mock_io)
                mock_io.tool_warning.assert_called_once_with(
                    "You should probably run aider in your project's directory, not your home dir."
                )
                self.assertIsNone(res)
        finally:
            os.chdir(orig_cwd)
            __import__("shutil").rmtree(str(fake_home))
