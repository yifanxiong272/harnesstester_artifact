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
        """Verify set_git_env restores the original environment value when original_value is not None."""
        var_name = "AIDER_TEST_ENV_VAR"
        initial_value = "original_value"
        temporary_value = "temporary_value"

        # Ensure initial state
        os.environ[var_name] = initial_value
        try:
            # Use the context manager form; inside the context the env var should be set to temporary_value
            with set_git_env(var_name, temporary_value, initial_value):
                self.assertEqual(os.environ.get(var_name), temporary_value)

            # After exiting the context manager, the original value should be restored
            self.assertEqual(os.environ.get(var_name), initial_value)
        finally:
            # Cleanup
            os.environ.pop(var_name, None)
