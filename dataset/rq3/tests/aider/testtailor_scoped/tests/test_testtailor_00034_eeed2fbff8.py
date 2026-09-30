import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.editor')
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
        """Trigger the exception path inside write_temp_file so os.close(fd) is executed."""
        fake_fd = 99
        fake_path = "/tmp/fakefile"

        with (
            patch("aider.editor.tempfile.mkstemp") as mock_mkstemp,
            patch("aider.editor.os.fdopen") as mock_fdopen,
            patch("aider.editor.os.close") as mock_close,
        ):
            mock_mkstemp.return_value = (fake_fd, fake_path)
            mock_fdopen.side_effect = RuntimeError("simulated fdopen failure")

            # The RuntimeError from fdopen should propagate and cause os.close(fd) to be called
            with self.assertRaises(RuntimeError):
                write_temp_file("some data")

            mock_close.assert_called_once_with(fake_fd)
