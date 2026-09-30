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
        """Ensure register_models raises the wrapped exception when YAML loads to None (non-iterable)."""
        import tempfile
        import os

        tmp = tempfile.mktemp(suffix=".yml")
        try:
            # Write YAML that parses to None but is non-empty (so pre-check passes)
            with open(tmp, "w") as f:
                f.write("null\n")

            from aider.models import register_models

            with self.assertRaises(Exception) as cm:
                register_models([tmp])

            msg = str(cm.exception)
            # Should include the file name and the original error about non-iterable / NoneType
            self.assertIn(f"Error loading model settings from {tmp}:", msg)
            self.assertTrue("NoneType" in msg or "not iterable" in msg)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
