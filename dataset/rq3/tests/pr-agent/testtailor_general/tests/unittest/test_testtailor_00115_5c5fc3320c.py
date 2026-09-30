import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.custom_merge_loader')
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
        """Trigger SecurityError when 'includes' attribute is present and silent is False."""
        # Minimal dummy object that satisfies the pre-checks in load()
        class DummyObj:
            pass

        obj = DummyObj()
        # Ensure settings_files is a non-empty list so loader proceeds to security checks
        obj.settings_files = ["ignored.toml"]
        # Simulate forbidden directive present
        obj.includes = True

        # Expect SecurityError to be raised when silent is False
        with self.assertRaises(SecurityError):
            load(obj, silent=False)
