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
        """Ensure openai_api_key is replaced in text with ...<last4> and original key removed."""
        class Args:
            pass

        args = Args()
        args.openai_api_key = "deadbeef1234"
        args.anthropic_api_key = None

        text = f"my secret is {args.openai_api_key} — do not share"
        result = scrub_sensitive_info(args, text)

        # last 4 chars of the key are "1234"
        self.assertIn("...1234", result)
        self.assertNotIn(args.openai_api_key, result)
        self.assertEqual(result, "my secret is ...1234 — do not share")
