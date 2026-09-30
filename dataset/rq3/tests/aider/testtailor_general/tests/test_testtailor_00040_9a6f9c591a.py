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
        """Simulate a failure during writing so the except branch calls os.close(fd)."""
        fd = 999
        fake_path = "/tmp/fakefile"
        # Create a fake context manager whose write raises
        mock_ctx = MagicMock()
        mock_file = MagicMock()
        mock_file.write.side_effect = RuntimeError("simulated write failure")
        mock_ctx.__enter__.return_value = mock_file
        mock_ctx.__exit__.return_value = False

        with patch("aider.editor.tempfile.mkstemp", return_value=(fd, fake_path)) as mkstemp_mock, \
             patch("aider.editor.os.fdopen", return_value=mock_ctx) as fdopen_mock, \
             patch("aider.editor.os.close") as close_mock:
            with self.assertRaises(RuntimeError):
                write_temp_file("data that triggers failure")

            # Verify mkstemp and fdopen were called and os.close was invoked with the fd
            mkstemp_mock.assert_called_once()
            fdopen_mock.assert_called_once_with(fd, "w")
            close_mock.assert_called_once_with(fd)
