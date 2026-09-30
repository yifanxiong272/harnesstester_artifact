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
        """Test that clone calls logger and _call with expected arguments."""
        url = "https://example.com/repo.git"
        directory = "/tmp/repo"

        # Prepare a dummy logger with a spyable .info method
        dummy_logger = type("L", (), {})()
        dummy_logger.info = unittest.mock.Mock()

        # Fake implementations to inject
        def fake_get_logger():
            return dummy_logger

        fake_stdout = "mocked stdout"
        fake__call = unittest.mock.Mock(return_value=fake_stdout)

        # Inject fakes into clone's globals
        gl = clone.__globals__
        orig_get_logger = gl.get("get_logger", None)
        orig__call = gl.get("_call", None)
        try:
            gl["get_logger"] = fake_get_logger
            gl["_call"] = fake__call

            # Call the function under test
            result = clone(url, directory)

            # clone doesn't return anything (None)
            self.assertIsNone(result)

            # _call should have been invoked with git clone arguments
            fake__call.assert_called_once_with("git", "clone", "--depth", "1", url, directory)

            # logger.info should have been called twice:
            # 1) with format string and url,directory
            # 2) with the stdout string
            self.assertEqual(dummy_logger.info.call_count, 2)
            first_call_args = dummy_logger.info.call_args_list[0][0]
            second_call_args = dummy_logger.info.call_args_list[1][0]

            self.assertEqual(first_call_args, ("Cloning %s to %s", url, directory))
            self.assertEqual(second_call_args, (fake_stdout,))

        finally:
            # Restore originals
            if orig_get_logger is not None:
                gl["get_logger"] = orig_get_logger
            else:
                gl.pop("get_logger", None)
            if orig__call is not None:
                gl["_call"] = orig__call
            else:
                gl.pop("_call", None)
