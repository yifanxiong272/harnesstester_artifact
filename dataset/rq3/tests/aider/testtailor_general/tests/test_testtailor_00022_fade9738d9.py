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
        """Ensure run_cmd takes the pexpect branch and returns captured interactive output."""
        mocker = unittest.mock
        # Force the conditions so run_cmd chooses the pexpect branch
        with mocker.patch("sys.stdin.isatty", return_value=True), \
             mocker.patch("platform.system", return_value="Linux"), \
             mocker.patch("pexpect.spawn") as mock_spawn:

            # Create a fake child process to simulate pexpect behavior
            mock_child = mocker.Mock()

            def fake_interact(*args, **kwargs):
                # Accept output_filter either as kwarg or positional
                output_filter = kwargs.get("output_filter")
                if output_filter is None and args:
                    output_filter = args[0]
                if output_filter:
                    # simulate two chunks of output as bytes
                    output_filter(b"first line\n")
                    output_filter(b"second line\n")
                return None

            mock_child.interact.side_effect = fake_interact
            mock_child.close.return_value = None
            mock_child.exitstatus = 0
            mock_spawn.return_value = mock_child

            # Act: call run_cmd which should route to run_cmd_pexpect
            rc, output = run_cmd("echo 'ignored by mock'", verbose=False, cwd=None)

            # Assert: return code comes from mocked child and output contains the produced lines
            self.assertEqual(rc, 0)
            self.assertIn("first line", output)
            self.assertIn("second line", output)
