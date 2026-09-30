import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.models')
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
        """register_models should skip files that contain only whitespace and not report them as loaded"""
        from aider.models import register_models, MODEL_SETTINGS
        import tempfile
        import os

        # Preserve original MODEL_SETTINGS to avoid side effects
        original_settings = MODEL_SETTINGS.copy()

        # Create a temporary file that exists but contains only whitespace
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
        try:
            tmp.write(b"   \n")
            tmp.close()

            # Call register_models with the whitespace-only file
            loaded = register_models([tmp.name])

            # Since the file contains only whitespace, it should be skipped and not reported as loaded
            self.assertEqual(loaded, [])

            # MODEL_SETTINGS should remain unchanged
            self.assertEqual(MODEL_SETTINGS, original_settings)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            # Restore original settings in case the function mutated anything
            MODEL_SETTINGS.clear()
            MODEL_SETTINGS.extend(original_settings)
