import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.utils')
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
        """Role=checkbox should use aria-checked to determine checkbox-state when AX not present."""
        # Minimal mocks to exercise the function path
        class MockNode:
            def __init__(self, aria_checked='true'):
                self.tag_name = 'div'
                self.attributes = {'role': 'checkbox', 'aria-checked': aria_checked, 'id': 'chk1'}
                self.ax_node = None
                self.children = []
                self.is_visible = True
                self.snapshot_node = None

            def get_all_children_text(self):
                return 'Label for checkbox'

        # Case where aria-checked is 'true' -> should be checked
        node = MockNode(aria_checked='true')
        desc = get_click_description(node)
        self.assertIn('role=checkbox', desc)
        self.assertIn('checkbox-state=checked', desc)
        self.assertIn('"Label for checkbox"', desc)

        # Case where aria-checked is 'false' -> should be unchecked
        node2 = MockNode(aria_checked='false')
        desc2 = get_click_description(node2)
        self.assertIn('role=checkbox', desc2)
        self.assertIn('checkbox-state=unchecked', desc2)
