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
        """Trigger the OSError handling path in run_cmd by making sys.stdin.isatty() raise OSError."""
        # create a dummy stdin whose isatty raises OSError
        class BadStdin:
            def isatty(self):
                raise OSError("bad fd")

        original_stdin = sys.stdin
        sys.stdin = BadStdin()
        try:
            called = []
            def error_printer(msg):
                called.append(msg)

            rc, msg = run_cmd("echo hi", error_print=error_printer)
            self.assertEqual(rc, 1)
            expected = "Error occurred while running command 'echo hi': bad fd"
            self.assertEqual(msg, expected)
            self.assertEqual(called, [expected])
        finally:
            sys.stdin = original_stdin
