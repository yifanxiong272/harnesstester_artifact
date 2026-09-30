import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.aws.__init__')
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
        """Verify that __getattr__ performs the lazy import and caches the attribute."""
        import importlib
        import types
        from unittest import mock

        # import the module that defines __getattr__ and _LAZY_IMPORTS
        aws_mod = importlib.import_module('browser_use.llm.aws')

        name = 'ChatAnthropicBedrock'
        module_path_expected = aws_mod._LAZY_IMPORTS[name][0]

        # Prepare a fake module with the expected attribute
        fake_attr = object()
        fake_module = types.SimpleNamespace(**{name: fake_attr})

        # Ensure attribute is not already cached
        if name in aws_mod.__dict__:
            del aws_mod.__dict__[name]

        with mock.patch('importlib.import_module', return_value=fake_module) as mock_import:
            # First access should trigger import_module and return the attribute
            val = getattr(aws_mod, name)
            self.assertIs(val, fake_attr)
            mock_import.assert_called_with(module_path_expected)

            # The attribute should now be cached in the module globals
            self.assertIn(name, aws_mod.__dict__)
            self.assertIs(aws_mod.__dict__[name], fake_attr)

            # Second access should use the cached value and not call import_module again
            val2 = getattr(aws_mod, name)
            self.assertIs(val2, fake_attr)
            self.assertEqual(mock_import.call_count, 1)

        # Clean up cached attribute to avoid side effects on other tests
        if name in aws_mod.__dict__:
            del aws_mod.__dict__[name]
