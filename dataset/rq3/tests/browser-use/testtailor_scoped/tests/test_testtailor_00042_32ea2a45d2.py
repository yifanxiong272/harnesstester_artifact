import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.serializer')
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
        # Create a ContentPartTextParam with typical text
        part = ContentPartTextParam(text='Hello, DeepSeek!')
        # Call the serializer text part function
        result = DeepSeekMessageSerializer._serialize_text_part(part)
        # The function should return the underlying text unchanged
        self.assertEqual(result, 'Hello, DeepSeek!')
        # Also ensure the return type is a string
        self.assertIsInstance(result, str)
