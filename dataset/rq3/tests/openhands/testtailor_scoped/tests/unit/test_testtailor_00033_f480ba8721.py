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
        # Preserve original platform and restore after test
        original_platform = sys.platform
        try:
            sys.platform = 'win32'
            prompt = 'please run bash -c "echo hello"; ensure bash works: bash'
            expected = prompt.replace('bash', 'powershell')
            result = refine_prompt(prompt)
            self.assertEqual(result, expected)
            # Also ensure all occurrences were replaced
            self.assertIn('powershell', result)
            self.assertNotIn('bash', result)
        finally:
            sys.platform = original_platform
