import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.serializer')
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
    def test_dom_tree_serializer_init_sets_internal_state_correctly(self):
        """Ensure DOMTreeSerializer.__init__ sets all internal fields as expected."""
        # Create a minimal EnhancedDOMTreeNode to pass as root_node
        from browser_use.dom.views import EnhancedDOMTreeNode, NodeType, SerializedDOMState
        from browser_use.dom.serializer.serializer import DOMTreeSerializer

        root = EnhancedDOMTreeNode(
            node_id=10,
            backend_node_id=20,
            node_type=NodeType.ELEMENT_NODE,
            node_name='DIV',
            node_value='',
            attributes={},
            is_scrollable=None,
            is_visible=True,
            absolute_position=None,
            target_id='target-1',
            frame_id=None,
            session_id=None,
            content_document=None,
            shadow_root_type=None,
            shadow_roots=None,
            parent_node=None,
            children_nodes=None,
            ax_node=None,
            snapshot_node=None,
        )

        # Case A: Without previous_cached_state and with default values
        serializer_default = DOMTreeSerializer(root_node=root)

        # Basic fields
        self.assertIs(serializer_default.root_node, root)
        self.assertEqual(serializer_default._interactive_counter, 1)
        self.assertIsInstance(serializer_default._selector_map, dict)
        self.assertDictEqual(serializer_default._selector_map, {})  # empty selector map
        self.assertIsNone(serializer_default._previous_cached_selector_map)
        self.assertIsInstance(serializer_default.timing_info, dict)
        self.assertDictEqual(serializer_default.timing_info, {})  # no timings yet
        self.assertIsInstance(serializer_default._clickable_cache, dict)
        self.assertDictEqual(serializer_default._clickable_cache, {})  # empty clickable cache

        # Bounding box / paint order defaults
        self.assertTrue(serializer_default.enable_bbox_filtering)
        self.assertEqual(
            serializer_default.containment_threshold,
            DOMTreeSerializer.DEFAULT_CONTAINMENT_THRESHOLD,
        )
        self.assertTrue(serializer_default.paint_order_filtering)
        self.assertIsNone(serializer_default.session_id)

        # Case B: Provide a previous_cached_state and explicit flags/threshold/session
        prev_state = SerializedDOMState(_root=None, selector_map={123: 'node-placeholder'})
        custom_threshold = 0.5
        serializer_custom = DOMTreeSerializer(
            root_node=root,
            previous_cached_state=prev_state,
            enable_bbox_filtering=False,
            containment_threshold=custom_threshold,
            paint_order_filtering=False,
            session_id='session-xyz',
        )

        # Validate field propagation from constructor args
        self.assertIs(serializer_custom.root_node, root)
        self.assertEqual(serializer_custom._interactive_counter, 1)
        self.assertIsInstance(serializer_custom._selector_map, dict)
        self.assertDictEqual(serializer_custom._selector_map, {})  # should still start empty
        # previous selector map should be taken from provided previous_cached_state
        self.assertIs(serializer_custom._previous_cached_selector_map, prev_state.selector_map)
        self.assertIsInstance(serializer_custom.timing_info, dict)
        self.assertDictEqual(serializer_custom.timing_info, {})
        self.assertIsInstance(serializer_custom._clickable_cache, dict)
        self.assertDictEqual(serializer_custom._clickable_cache, {})

        # Flags and values
        self.assertFalse(serializer_custom.enable_bbox_filtering)
        self.assertEqual(serializer_custom.containment_threshold, custom_threshold)
        self.assertFalse(serializer_custom.paint_order_filtering)
        self.assertEqual(serializer_custom.session_id, 'session-xyz')
