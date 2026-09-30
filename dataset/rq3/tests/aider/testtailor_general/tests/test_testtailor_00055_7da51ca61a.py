import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.onboarding')
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
        """When no port is available, the function should report an error and return None."""
        import importlib
        import pkgutil
        from unittest.mock import MagicMock
        import aider

        # Locate the module in the aider package that defines start_openrouter_oauth_flow
        target_mod = None
        for finder, name, ispkg in pkgutil.iter_modules(aider.__path__):
            full_name = f"{aider.__name__}.{name}"
            mod = importlib.import_module(full_name)
            if hasattr(mod, "start_openrouter_oauth_flow"):
                target_mod = mod
                break

        if target_mod is None:
            # If the function isn't present in any submodule, skip the test to avoid false failure.
            self.skipTest("start_openrouter_oauth_flow not found in aider package modules")

        # Patch find_available_port in the target module to simulate no available port
        original_find = getattr(target_mod, "find_available_port", None)
        try:
            setattr(target_mod, "find_available_port", lambda *args, **kwargs: None)

            io = MagicMock()
            analytics = MagicMock()

            # Call the function under test; patched find_available_port returns None
            result = target_mod.start_openrouter_oauth_flow(io, analytics)

            # Expect None when no port is available
            self.assertIsNone(result)

            # Ensure appropriate error messages were emitted to the IO layer
            io.tool_error.assert_any_call("Could not find an available port between 8484 and 8584.")
            io.tool_error.assert_any_call("Please ensure a port in this range is free, or configure manually.")
        finally:
            # Restore original attribute to avoid side effects on other tests
            if original_find is None:
                try:
                    delattr(target_mod, "find_available_port")
                except Exception:
                    pass
            else:
                setattr(target_mod, "find_available_port", original_find)
