import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.inspector.static')
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
    def test_case_01(self):
        """When load_content raises an exception, _load_file should return the error message with the traceback."""
        # Preserve original load_content if present
        orig = _load_file.__globals__.get("load_content", None)
        try:
            # Replace load_content in the _load_file globals with one that raises
            def _bad_load_content(*args, **kwargs):
                raise RuntimeError("boom")
            _load_file.__globals__["load_content"] = _bad_load_content

            result = _load_file("some_file", None, None)

            # It should return the error prefix and include the exception text from the traceback
            self.assertTrue(result.startswith("Error loading content. "))
            self.assertIn("RuntimeError: boom", result)
        finally:
            # Restore original load_content to avoid side effects for other tests
            if orig is None:
                del _load_file.__globals__["load_content"]
            else:
                _load_file.__globals__["load_content"] = orig
