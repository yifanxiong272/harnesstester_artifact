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
        """Ensure register_models surfaces errors when YAML is a mapping (not a list), causing ModelSettings construction to fail."""
        import tempfile
        import os

        from aider.models import register_models

        tmp = tempfile.mktemp(suffix=".yml")
        try:
            # Write a YAML mapping (dict) instead of a list. safe_load will return a dict,
            # the for-loop will iterate its keys (strings), and ModelSettings(**key) will raise,
            # which should be caught and re-raised with our target message.
            with open(tmp, "w") as f:
                f.write("name: test-model\n")

            with self.assertRaises(Exception) as cm:
                register_models([tmp])

            msg = str(cm.exception)
            self.assertIn("Error loading model settings from", msg)
            self.assertIn(tmp, msg)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
