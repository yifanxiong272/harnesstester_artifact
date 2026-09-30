import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.serializer')
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
		"""Test DOMTreeSerializer._safe_parse_number handles valid numbers and falls back to default on errors."""
		# Create serializer instance (root_node not used by _safe_parse_number)
		serializer = DOMTreeSerializer(root_node=None)

		# Valid numeric strings (including negative and decimal)
		self.assertEqual(serializer._safe_parse_number("123.45", default=0.0), 123.45)
		self.assertEqual(serializer._safe_parse_number("-123.45", default=0.0), -123.45)
		self.assertEqual(serializer._safe_parse_number("  1e3  ", default=0.0), 1000.0)

		# Invalid numeric strings -> should return provided default
		self.assertEqual(serializer._safe_parse_number("not_a_number", default=42.0), 42.0)
		self.assertEqual(serializer._safe_parse_number("", default=-1.0), -1.0)

		# Non-string input that triggers TypeError (e.g., None) -> should return default
		self.assertEqual(serializer._safe_parse_number(None, default=3.14), 3.14)

		# Some other non-convertible type
		class Dummy:
			def __str__(self):
				# Make float(Dummy()) raise TypeError by returning an object that float() can't handle
				return "nan_value"

		# Although float("nan_value") raises ValueError, ensure default is returned
		self.assertEqual(serializer._safe_parse_number(Dummy(), default=9.99), 9.99)
