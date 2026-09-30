import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.models')
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
        """validate_variables returns keys_in_environment=True when all vars present"""
        import os
        import sys
        import inspect

        # Try to find the validate_variables function in loaded modules,
        # falling back to trying common package roots.
        validate_func = None
        for mod in list(sys.modules.values()):
            if not mod:
                continue
            if hasattr(mod, "validate_variables"):
                candidate = getattr(mod, "validate_variables")
                if inspect.isfunction(candidate):
                    validate_func = candidate
                    break

        # As an additional fallback, try importing the top-level package 'aider'
        # which is used elsewhere in the project tests.
        if validate_func is None:
            try:
                import aider  # type: ignore
                if hasattr(aider, "validate_variables"):
                    candidate = getattr(aider, "validate_variables")
                    if inspect.isfunction(candidate):
                        validate_func = candidate
            except Exception:
                pass

        self.assertIsNotNone(validate_func, "Could not find validate_variables in any loaded module")

        vars_to_check = ["TEST_ENV_VAR_A", "TEST_ENV_VAR_B"]
        # Ensure the environment contains the variables so the function should
        # report keys_in_environment=True and an empty missing_keys list.
        old_values = {}
        try:
            for v in vars_to_check:
                old_values[v] = os.environ.get(v)
                os.environ[v] = "1"

            result = validate_func(vars_to_check)

            self.assertIsInstance(result, dict)
            self.assertTrue(result.get("keys_in_environment"))
            self.assertIn("missing_keys", result)
            self.assertEqual(result["missing_keys"], [])
        finally:
            # Restore previous environment state
            for v in vars_to_check:
                if old_values[v] is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = old_values[v]
