import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.log.__init__')
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
        """Verify analytics_filter returns the analytics flag when present and defaults to False."""
        # analytics present and True
        self.assertTrue(analytics_filter({'extra': {'analytics': True}}))

        # analytics present and False
        self.assertFalse(analytics_filter({'extra': {'analytics': False}}))

        # extra present but analytics missing -> default False
        self.assertFalse(analytics_filter({'extra': {}}))

        # extra missing entirely -> default False
        self.assertFalse(analytics_filter({}))
