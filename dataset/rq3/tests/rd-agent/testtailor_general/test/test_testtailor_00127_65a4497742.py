import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.core.utils')
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
        """Test parse_json returns parsed object for valid JSON and raises ValueError for invalid JSON."""
        # valid JSON should be parsed and returned as Python object
        valid_response = '{"name": "Alice", "age": 30, "skills": ["python", "testing"]}'
        result = parse_json(valid_response)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "Alice")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["skills"], ["python", "testing"])

        # invalid JSON should raise ValueError with the expected message
        invalid_response = '{"name": "Bob", "age": 25'  # missing closing brace
        with self.assertRaises(ValueError) as cm:
            parse_json(invalid_response)
        err_text = str(cm.exception)
        self.assertIn("Failed to parse response", err_text)
        self.assertIn(invalid_response, err_text)
