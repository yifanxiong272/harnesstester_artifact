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
        """DOCUMENT_FRAGMENT_NODE should be serialized into a <template shadowroot=...> wrapper."""
        serializer = HTMLSerializer()

        # Minimal fake node that has the attributes the serializer accesses for DOCUMENT_FRAGMENT_NODE
        node = type('DummyNode', (), {})()
        node.node_type = NodeType.DOCUMENT_FRAGMENT_NODE
        node.shadow_root_type = 'CLOSED'  # should be lowercased by serializer
        node.children = []  # no children -> empty template body

        html = serializer.serialize(node, depth=0)
        self.assertEqual(html, '<template shadowroot="closed"></template>')
