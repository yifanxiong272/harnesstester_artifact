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
        """Ensure Optional[...] special parameter with Union origin is handled."""
        registry = Registry()

        # Define an action that declares a special parameter present in the registry's
        # special params map. Annotate it as Optional[list[str]] so get_origin(...) is Union
        # and the code path that extracts the non-None arg is exercised.
        def my_action(available_file_paths: Optional[list[str]]):
            # Return the received value so we can assert it was passed through correctly
            return available_file_paths

        # Normalize the function signature (this should trigger the Union handling branch)
        normalized_func, param_model = registry._normalize_action_function_signature(my_action, "desc")

        # The normalized function should expose the special param as a keyword-only argument
        sig = signature(normalized_func)
        self.assertIn("available_file_paths", sig.parameters)

        # Call the normalized async wrapper and verify it forwards the special param correctly.
        result = asyncio.run(normalized_func(params=None, available_file_paths=["/tmp/path"]))
        self.assertEqual(result, ["/tmp/path"])
