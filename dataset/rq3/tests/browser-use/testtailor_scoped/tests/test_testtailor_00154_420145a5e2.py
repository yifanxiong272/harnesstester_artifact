import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.utils')
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
		"""collect_sensitive_data_values should return an empty dict for falsy inputs."""
		# None should trigger the early return branch
		result_none = collect_sensitive_data_values(None)
		self.assertIsInstance(result_none, dict)
		self.assertEqual(result_none, {})

		# An empty dict is also falsy and should produce the same result
		result_empty = collect_sensitive_data_values({})
		self.assertIsInstance(result_empty, dict)
		self.assertEqual(result_empty, {})
