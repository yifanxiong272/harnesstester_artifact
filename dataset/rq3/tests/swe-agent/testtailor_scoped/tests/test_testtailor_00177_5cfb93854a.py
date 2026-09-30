import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """Ensure interpret uses only the last line when extracting numbers."""
        class DummyLogger:
            def warning(self, msg):
                self.last_warning = msg
            def error(self, msg):
                self.last_error = msg

        class Dummy:
            def __init__(self):
                self.logger = DummyLogger()

        dummy = Dummy()
        # Include numbers on earlier lines that should be ignored;
        # only the numbers on the last line should be returned.
        response = "Line with number 123\nAnother line 456\nFinal line: choices 5 and 7"
        result = Preselector.interpret(dummy, response)
        self.assertEqual(result, [5, 7])
