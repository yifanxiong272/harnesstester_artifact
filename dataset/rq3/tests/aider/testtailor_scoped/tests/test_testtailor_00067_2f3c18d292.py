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
        """Ensure anthropic API key is scrubbed and replaced with last 4 characters."""
        # Create args with an anthropic API key and no OpenAI key so the anthropic branch runs
        args = MagicMock()
        args.openai_api_key = None
        args.anthropic_api_key = "anthropic_secret_ABCDEF1234"

        # Text contains the anthropic key twice to ensure replace() handles multiple occurrences
        text = f"Key1: {args.anthropic_api_key}; Key2: {args.anthropic_api_key}"

        # Call the function under test
        scrubbed = scrub_sensitive_info(args, text)

        # Last 4 characters expected
        expected_tail = args.anthropic_api_key[-4:]

        # Assertions: full key should not be present, masked value should be present for both occurrences
        self.assertNotIn(args.anthropic_api_key, scrubbed)
        self.assertIn(f"...{expected_tail}", scrubbed)
        self.assertEqual(scrubbed.count(f"...{expected_tail}"), 2)
