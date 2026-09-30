import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.reasoning_tags')
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
        """Test that replace_reasoning_tags returns immediately when text is falsy."""
        from aider.reasoning_tags import replace_reasoning_tags

        # None should be returned as-is (and not raise)
        self.assertIsNone(replace_reasoning_tags(None, "think"))

        # Empty string should be returned as-is
        self.assertEqual(replace_reasoning_tags("", "think"), "")
