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
        """Ensure HTMLSerializer handles DOCUMENT_NODE by serializing its children."""
        # Minimal fake node to mimic required attributes for serialization
        class FakeNode:
            def __init__(self, node_type, node_value=None):
                self.node_type = node_type
                self.node_value = node_value
                # Document-specific
                self.children_and_shadow_roots = []
                # Element/text node expected attributes (not used for this test but present)
                self.children_nodes = []
                self.shadow_roots = None
                self.attributes = {}
                self.node_name = ''
                self.content_document = None

            @property
            def tag_name(self):
                return self.node_name.lower() if self.node_name else ''

        # Create a text child node
        text_node = FakeNode(NodeType.TEXT_NODE, node_value="hello")
        # Create document node and attach the text child
        doc_node = FakeNode(NodeType.DOCUMENT_NODE)
        doc_node.children_and_shadow_roots = [text_node]

        serializer = HTMLSerializer()
        output = serializer.serialize(doc_node)

        self.assertEqual(output, "hello")
