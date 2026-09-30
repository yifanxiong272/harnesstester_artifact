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
        """Serialize should process a DOCUMENT_NODE by serializing its children."""
        # Create serializer
        serializer = HTMLSerializer()

        # Minimal dummy node objects with required attributes
        class Dummy:
            pass

        # Create a text child node
        text_node = Dummy()
        text_node.node_type = NodeType.TEXT_NODE
        text_node.node_value = 'hello & <world>'

        # Create a document node with children_and_shadow_roots containing the text node
        doc_node = Dummy()
        doc_node.node_type = NodeType.DOCUMENT_NODE
        doc_node.children_and_shadow_roots = [text_node]

        # Serialize document node
        output = serializer.serialize(doc_node)

        # Expect the text to be HTML-escaped
        self.assertEqual(output, 'hello &amp; &lt;world&gt;')
