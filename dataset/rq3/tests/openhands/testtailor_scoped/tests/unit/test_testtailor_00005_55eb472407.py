import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.docker.docker_runtime')
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
        """Test that _is_retryablewait_until_alive_error correctly unwraps tenacity.RetryError
        and classifies the underlying exception as retryable or not, including nested RetryError.
        """
        func = _is_retryablewait_until_alive_error
        # Get the tenacity module object from the function's globals to avoid top-level imports
        tenacity_mod = func.__globals__['tenacity']

        class DummyAttempt:
            def __init__(self, exc):
                self._exc = exc

            def exception(self):
                return self._exc

        # Case 1: underlying exception is a builtin ConnectionError -> should be retryable (True)
        retry_err_conn = tenacity_mod.RetryError(DummyAttempt(ConnectionError("connection failed")))
        self.assertTrue(func(retry_err_conn))

        # Case 2: underlying exception is a non-retryable exception -> should be False
        retry_err_non = tenacity_mod.RetryError(DummyAttempt(ValueError("bad value")))
        self.assertFalse(func(retry_err_non))

        # Case 3: nested RetryError where inner contains a retryable exception -> should recurse and return True
        inner_retry = tenacity_mod.RetryError(DummyAttempt(ConnectionError("inner connection failed")))
        outer_retry = tenacity_mod.RetryError(DummyAttempt(inner_retry))
        self.assertTrue(func(outer_retry))
