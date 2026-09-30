import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.cloud_events')
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
        """Trigger the file size validator raising path by patching the validator's global MAX_FILE_CONTENT_SIZE."""
        # Import module and class under test
        mod = __import__('browser_use.beta.service', fromlist=['CreateAgentOutputFileEvent'])
        cls = getattr(mod, 'CreateAgentOutputFileEvent')

        # Retrieve the raw function object for the validator from the class dict
        validator_entry = cls.__dict__['validate_file_size']
        # If decorated as classmethod, get the underlying function
        raw_func = validator_entry.__func__ if isinstance(validator_entry, classmethod) else validator_entry

        # Patch the function's global MAX_FILE_CONTENT_SIZE to a very small value so a short base64 string exceeds it
        globs = raw_func.__globals__
        had_original = 'MAX_FILE_CONTENT_SIZE' in globs
        if had_original:
            original_value = globs['MAX_FILE_CONTENT_SIZE']
        try:
            globs['MAX_FILE_CONTENT_SIZE'] = 1  # threshold 1 byte to force the raise for a small payload
            # 'AA' -> estimated_size = 2 * 3 / 4 = 1.5 > 1 should raise
            with self.assertRaises(ValueError) as cm:
                cls.validate_file_size('AA')
            message = str(cm.exception)
            self.assertIn('File content exceeds maximum size', message)
            self.assertIn('MB', message)
        finally:
            # Restore original global to avoid side effects
            if had_original:
                globs['MAX_FILE_CONTENT_SIZE'] = original_value
            else:
                try:
                    del globs['MAX_FILE_CONTENT_SIZE']
                except Exception:
                    pass
