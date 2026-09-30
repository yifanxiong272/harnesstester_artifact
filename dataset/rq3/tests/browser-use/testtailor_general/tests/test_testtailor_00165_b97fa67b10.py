import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.views')
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
		"""Verify filter_dynamic_classes filters out any class containing dynamic patterns (case-insensitive),
		and returns the remaining classes sorted for deterministic output."""
		# Mixed classes where several should be removed because they contain dynamic patterns.
		input_classes = "btn primary hover:button isOpen active-state stable-class Highlighted currently"
		# Expected to keep only 'btn', 'primary', and 'stable-class', sorted lexicographically.
		self.assertEqual(filter_dynamic_classes(input_classes), "btn primary stable-class")

		# Order-independence: input order should not affect sorted output
		input_classes2 = "stable-class btn primary"
		self.assertEqual(filter_dynamic_classes(input_classes2), "btn primary stable-class")

		# Substring matching and case-insensitivity: 'MY-hovered' contains 'hover' (case-insensitive) -> removed
		input_classes3 = "MY-hovered SAFE_CLASS normal"
		self.assertEqual(filter_dynamic_classes(input_classes3), "SAFE_CLASS normal")

		# No dynamic classes -> should return sorted classes
		input_classes4 = "z a m"
		self.assertEqual(filter_dynamic_classes(input_classes4), "a m z")

		# Single class that is dynamic should result in empty string (filtered out)
		self.assertEqual(filter_dynamic_classes("isDisabled"), "")

		# Classes that include dynamic words as substrings should be removed (e.g., 'currentness' contains 'current')
		input_classes5 = "keep currentness-flag keep2"
		# 'currentness-flag' contains 'current' so it should be filtered out
		self.assertEqual(filter_dynamic_classes(input_classes5), "keep keep2")
