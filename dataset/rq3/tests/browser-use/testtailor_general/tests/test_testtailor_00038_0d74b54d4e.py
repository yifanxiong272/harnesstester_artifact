import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.html_serializer')
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
        """Verify that the extract_links flag is stored on initialization."""
        # Default should be False
        serializer_default = HTMLSerializer()
        self.assertFalse(serializer_default.extract_links)

        # Explicit True should be preserved
        serializer_true = HTMLSerializer(extract_links=True)
        self.assertTrue(serializer_true.extract_links)

        # Explicit False should be preserved
        serializer_false = HTMLSerializer(extract_links=False)
        self.assertFalse(serializer_false.extract_links)
