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
        """Ensure _is_retryablewait_until_alive_error unwraps tenacity.RetryError via last_attempt.exception()."""
        # Fake attempt object that mimics tenacity's attempt with an exception() method
        class FakeAttempt:
            def __init__(self, exc):
                self._exc = exc

            def exception(self):
                return self._exc

        # Case 1: a RetryError whose last_attempt.exception() returns a ConnectionError
        retry_err = tenacity.RetryError(FakeAttempt(ConnectionError("connection refused")))
        self.assertTrue(_is_retryablewait_until_alive_error(retry_err))

        # Case 2: nested RetryError -> RetryError -> ConnectionError to exercise recursion
        inner = tenacity.RetryError(FakeAttempt(ConnectionError("inner refused")))
        outer = tenacity.RetryError(FakeAttempt(inner))
        self.assertTrue(_is_retryablewait_until_alive_error(outer))
