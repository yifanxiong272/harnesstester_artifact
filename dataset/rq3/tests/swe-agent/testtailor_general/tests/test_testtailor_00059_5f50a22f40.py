import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.common')
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
        """complete the test case here"""
        data = [
            "hello\nworld",
            {"a": "abcdefghijk"},
            ["x\ny", 42],
        ]
        result = _shorten_strings(data, max_length=10)
        expected = [
            "hello\\n...",
            {"a": "abcdefg..."},
            ["x\\ny...", 42],
        ]
        self.assertEqual(result, expected)
