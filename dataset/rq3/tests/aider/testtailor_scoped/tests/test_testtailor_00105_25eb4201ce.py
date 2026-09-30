import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.base_coder')
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
        """Test that Coder.clone delegates to Coder.create and copies state while allowing overrides."""
        # Create a base coder without directly using Model (allow create to pick default)
        io = InputOutput(yes=True)
        base = Coder.create(main_model=None, edit_format="diff", io=io, fnames=[], total_cost=3.14, auto_lint=True)

        # Sanity checks on base
        self.assertEqual(base.total_cost, 3.14)
        self.assertTrue(base.auto_lint)

        # Clone the coder, overriding auto_lint
        cloned = base.clone(auto_lint=False)

        # Ensure we got a new object
        self.assertIsNot(base, cloned)

        # Core properties should be preserved
        self.assertIs(cloned.main_model, base.main_model)
        self.assertIs(cloned.io, base.io)
        self.assertEqual(cloned.total_cost, base.total_cost)
        self.assertEqual(cloned.abs_fnames, base.abs_fnames)

        # The override should have taken effect
        self.assertFalse(cloned.auto_lint)

        # original_kwargs should be set on the new coder and should include keys from the creation
        self.assertIsInstance(getattr(cloned, "original_kwargs", None), dict)
        self.assertIn("total_cost", cloned.original_kwargs)
        self.assertIn("auto_lint", cloned.original_kwargs)
        self.assertEqual(cloned.original_kwargs.get("total_cost"), base.total_cost)
        self.assertIs(cloned.original_kwargs.get("auto_lint"), False)
