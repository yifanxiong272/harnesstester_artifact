import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.format_settings')
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
        """Ensure anthropic API key is scrubbed to last 4 characters in the text."""
        # Create a simple args object with the needed attributes
        class Args:
            pass

        args = Args()
        # Ensure openai branch does not trigger
        args.openai_api_key = None
        # Provide an anthropic key with known last 4 characters
        args.anthropic_api_key = "anthropic-secret-ABCD1234"

        # Text contains the full anthropic API key
        text = f"Here is the key: {args.anthropic_api_key} - do not leak."

        # Call the function under test
        result = scrub_sensitive_info(args, text)

        # The full key should be replaced with '...1234'
        self.assertIn("...1234", result)
        self.assertNotIn(args.anthropic_api_key, result)

        # Other parts of the text should remain unchanged
        self.assertIn("Here is the key:", result)
        self.assertIn("- do not leak.", result)
