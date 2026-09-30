import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.abstract')
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
        """Verify CombinedRunHooks.hooks returns the internal list (not a copy) and reflects additions."""
        combined = CombinedRunHooks()

        # Initially the hooks list should be empty
        self.assertEqual(combined.hooks, [])
        self.assertIs(combined.hooks, combined._hooks)

        # Add a couple of hooks and verify they appear in the returned list
        h1 = RunHook()
        h2 = RunHook()
        combined.add_hook(h1)
        combined.add_hook(h2)

        self.assertEqual(combined.hooks, [h1, h2])
        self.assertIs(combined.hooks, combined._hooks)

        # Mutating the returned list should mutate the internal list as well
        combined.hooks.append("marker")
        self.assertIn("marker", combined._hooks)
        self.assertIs(combined.hooks, combined._hooks)
