import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.utils')
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
        """When validate_provider_token returns None, identify_token should raise ValueError."""
        token = "fake-token"
        base_domain = None

        # Patch the validate_provider_token where identify_token actually looks it up.
        # Determine the module that contains identify_token, then patch that module's attribute.
        import importlib
        import asyncio

        module = importlib.import_module(identify_token.__module__)

        with unittest.mock.patch.object(
            module,
            "validate_provider_token",
            new_callable=unittest.mock.AsyncMock,
        ) as mock_validate:
            mock_validate.return_value = None

            with self.assertRaises(ValueError) as ctx:
                asyncio.run(identify_token(token, base_domain))

            self.assertEqual(str(ctx.exception), "Token is invalid.")
            mock_validate.assert_awaited_once_with(unittest.mock.ANY, base_domain)
