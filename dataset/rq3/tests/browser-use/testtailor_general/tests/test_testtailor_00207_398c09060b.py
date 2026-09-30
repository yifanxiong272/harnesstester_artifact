import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.clickable_elements')
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
        """Non-element nodes (e.g., text nodes) must be treated as non-interactive and return False."""
        # Create a minimal dummy object that mimics just enough of the node interface.
        dummy = type("DummyNode", (), {})()
        dummy.node_type = NodeType.TEXT_NODE  # Not an ELEMENT_NODE -> should trigger early return False

        result = ClickableElementDetector.is_interactive(dummy)
        self.assertFalse(result)
