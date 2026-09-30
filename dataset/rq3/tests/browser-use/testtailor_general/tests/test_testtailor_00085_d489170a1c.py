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
    def test_case_XX(self):
        """Minimal node: ensure tag_name is returned as the description."""
        class DummyNode:
            def __init__(self):
                self.tag_name = 'button'
                self.attributes = {}
                self.children = []
                self.ax_node = None
                self.snapshot_node = None
                self.is_visible = True

            def get_all_children_text(self):
                return ''

        node = DummyNode()
        desc = get_click_description(node)
        self.assertEqual(desc, 'button')
