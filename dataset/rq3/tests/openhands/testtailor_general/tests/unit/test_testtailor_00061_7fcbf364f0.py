import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.fn_call_converter')
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
        """Ensure refine_prompt replaces 'bash' with 'powershell' when running on Windows."""
        original_platform = sys.platform
        try:
            # Force the platform to Windows to hit the branch
            sys.platform = 'win32'
            prompt = 'Run this bash command: bash -c "echo hello"\nAlso a mention of bash.'
            result = refine_prompt(prompt)
            # All occurrences of 'bash' should be replaced
            self.assertNotIn('bash', result)
            self.assertIn('powershell', result)
            self.assertEqual(result.count('powershell'), 3)
        finally:
            # Restore original platform to avoid side effects on other tests
            sys.platform = original_platform
