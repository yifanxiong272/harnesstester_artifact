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
        """Ensure Optional special-parameter annotations (Union[..., None])
        are handled by the Union branch that extracts the non-None type.
        """
        # Create registry instance
        reg = Registry()

        # Build a simple function that declares a special parameter named 'page'
        # and annotate it as Optional[int] using typing imported at runtime.
        typing = __import__('typing')
        def my_action(page=None):
            # Return the received value so we can assert it was passed through.
            return page

        # Ensure the annotation is Optional[int] (i.e. Union[int, None])
        my_action.__annotations__ = {'page': typing.Optional[int]}

        # Monkeypatch the registry to treat 'page' as a special param with expected type int.
        reg._get_special_param_types = lambda: {'page': int}

        # Should not raise; should return a normalized async wrapper and a param model
        normalized, param_model = reg._normalize_action_function_signature(my_action, 'desc', None)

        # Basic sanity checks on return values
        self.assertTrue(callable(normalized))
        self.assertTrue(hasattr(param_model, 'model_validate') or hasattr(param_model, 'model_dump'))

        # The normalized wrapper signature should include 'page' as a keyword-only special param
        inspect = __import__('inspect')
        params = inspect.signature(normalized).parameters
        self.assertIn('page', params)

        # Call the normalized async wrapper and ensure the special param is passed through correctly.
        asyncio = __import__('asyncio')
        result = asyncio.run(normalized(params=None, page=42))
        self.assertEqual(result, 42)
