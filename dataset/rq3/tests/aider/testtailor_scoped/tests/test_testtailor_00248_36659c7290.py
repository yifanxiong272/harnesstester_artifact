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
        """When CWD is the user's home and no git_root is provided, setup_git should warn and return."""
        io = MagicMock()
        # Simulate being run from the user's home directory
        with patch("pathlib.Path.cwd", return_value=Path.home()):
            result = setup_git(None, io)

        io.tool_warning.assert_called_once_with(
            "You should probably run aider in your project's directory, not your home dir."
        )
        self.assertIsNone(result)
