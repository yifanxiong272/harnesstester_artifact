import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.registry.service')
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
        """action() must raise if both 'domains' and 'allowed_domains' are provided (they are aliases)."""
        registry = Registry()
        with self.assertRaises(ValueError) as cm:
            # This should raise immediately from the decorator factory
            registry.action("desc", domains=["example.com"], allowed_domains=["example.org"])
        self.assertEqual(
            str(cm.exception),
            "Cannot specify both 'domains' and 'allowed_domains' - they are aliases for the same parameter",
        )
