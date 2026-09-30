import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.utils')
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
		"""Ensure top-level get_key_info delegates to Utils.get_key_info and returns expected tuples."""
		# Known mapping from key_map
		code, vk = get_key_info('Enter')
		self.assertEqual(code, 'Enter')
		self.assertEqual(vk, 13)

		# Single alphabetic character -> dynamic letter mapping
		code_a, vk_a = get_key_info('a')
		self.assertEqual(code_a, 'KeyA')
		self.assertEqual(vk_a, ord('A'))

		# Single digit -> dynamic digit mapping
		code_5, vk_5 = get_key_info('5')
		self.assertEqual(code_5, 'Digit5')
		self.assertEqual(vk_5, ord('5'))

		# Space alias should map to Space
		code_space, vk_space = get_key_info(' ')
		self.assertEqual(code_space, 'Space')
		self.assertEqual(vk_space, 32)

		# Unknown multi-character key -> fallback with None virtual key code
		code_unknown, vk_unknown = get_key_info('SomeNonexistentKey')
		self.assertEqual(code_unknown, 'SomeNonexistentKey')
		self.assertIsNone(vk_unknown)
