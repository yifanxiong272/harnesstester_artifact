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
        """Ensure DOCUMENT_FRAGMENT_NODE serializes to a <template> with its children."""
        serializer = HTMLSerializer()

        # Minimal fake node to mimic EnhancedDOMTreeNode for this test
        class FakeNode:
            def __init__(self, node_type, node_value=None, shadow_root_type=None, children=None):
                self.node_type = node_type
                self.node_value = node_value
                self.shadow_root_type = shadow_root_type
                # The serializer accesses .children for document fragments
                self.children = children or []

        # Child text node that should be escaped by the serializer
        text_child = FakeNode(NodeType.TEXT_NODE, node_value='Hello & <world>')

        # Document fragment (shadow root) with a closed shadow root type
        frag = FakeNode(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='Closed', children=[text_child])

        output = serializer.serialize(frag)

        expected = '<template shadowroot="closed">Hello &amp; &lt;world&gt;</template>'
        self.assertEqual(output, expected)
