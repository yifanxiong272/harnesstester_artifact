import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.gerrit_provider')
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
        """Test that _call returns decoded stdout and calls subprocess.run with expected args."""
        # Prepare a fake subprocess.CompletedProcess-like object
        fake_result = unittest.mock.Mock()
        fake_result.stdout = b"hello world"
        fake_result.stderr = b""
        # Patch subprocess.run so no real command is executed
        with unittest.mock.patch("subprocess.run", return_value=fake_result) as mock_run:
            # Call the function under test with a couple of command parts and a kwarg
            result = _call("cmd", "arg1", cwd="/tmp")

            # Verify the returned value is decoded stdout
            self.assertEqual(result, "hello world")

            # Verify subprocess.run was called exactly once
            mock_run.assert_called_once()

            # Inspect the call to ensure the command tuple and keyword arguments were passed through
            called_args, called_kwargs = mock_run.call_args
            # First positional argument to subprocess.run should be the tuple of command parts
            self.assertEqual(called_args[0], ("cmd", "arg1"))
            # stdout and stderr should have been set to subprocess.PIPE
            self.assertEqual(called_kwargs.get("stdout"), subprocess.PIPE)
            self.assertEqual(called_kwargs.get("stderr"), subprocess.PIPE)
            # check should be True
            self.assertTrue(called_kwargs.get("check"))
            # the extra kwarg should have been forwarded
            self.assertEqual(called_kwargs.get("cwd"), "/tmp")
