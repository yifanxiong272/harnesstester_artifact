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
        """When a closing tag exists but the opening tag is missing, everything before the
        closing tag should be removed and only the text after the closing tag should remain.
        This exercises the branch that splits on the closing tag and returns parts[1].
        """
        # Closing tag present but no opening tag -> regex won't remove it
        text = "Text that should be removed </think> This is the kept content  "
        result = remove_reasoning_content(text, "think")
        self.assertEqual(result, "This is the kept content")
