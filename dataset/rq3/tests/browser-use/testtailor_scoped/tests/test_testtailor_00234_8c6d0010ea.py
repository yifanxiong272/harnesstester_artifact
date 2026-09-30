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
        """Calling execute_action with an unknown action should raise ValueError."""
        reg = Registry()
        with self.assertRaises(ValueError) as cm:
            # execute_action is async, run it in the event loop
            asyncio.run(reg.execute_action("nonexistent_action", {}))
        self.assertIn("Action nonexistent_action not found", str(cm.exception))
