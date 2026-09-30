import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.run_cmd')
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
        """Ensure the verbose branch prints the 'Using run_cmd_subprocess' message."""
        command = "echo hello"

        with patch("subprocess.Popen") as mock_popen, patch("builtins.print") as mock_print:
            # Prepare a mock process whose stdout.read returns empty immediately to end loop
            mock_process = MagicMock()
            mock_stdout = MagicMock()
            mock_stdout.read.return_value = ""  # causes the read loop to exit immediately
            mock_process.stdout = mock_stdout
            mock_process.returncode = 0
            mock_process.wait = MagicMock()
            mock_popen.return_value = mock_process

            rc, output = run_cmd_subprocess(command, verbose=True)

            # Verify subprocess was invoked and function returned expected values
            mock_popen.assert_called_once()
            self.assertEqual(rc, 0)
            self.assertEqual(output, "")

            # Verify the verbose print at the start was called with the command
            mock_print.assert_any_call("Using run_cmd_subprocess:", command)
