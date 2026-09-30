# file: browser_use/dom/serializer/serializer.py:882-1085
# asked: {"lines": [885, 886, 889, 890, 891, 892, 893, 894, 895, 897, 898, 899, 901, 903, 904, 905, 906, 907, 908, 911, 912, 913, 914, 915, 916, 917, 918, 920, 922, 924, 925, 926, 927, 928, 929, 930, 931, 932, 934, 937, 938, 940, 941, 942, 943, 945, 948, 949, 950, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 970, 971, 972, 973, 974, 975, 976, 978, 979, 981, 982, 983, 984, 986, 989, 990, 992, 993, 994, 995, 996, 998, 1000, 1002, 1003, 1005, 1006, 1007, 1008, 1010, 1011, 1013, 1015, 1017, 1018, 1020, 1023, 1024, 1025, 1026, 1028, 1030, 1032, 1033, 1035, 1037, 1040, 1041, 1042, 1043, 1046, 1047, 1049, 1051, 1053, 1054, 1055, 1056, 1058, 1059, 1062, 1063, 1064, 1065, 1066, 1070, 1071, 1072, 1074, 1076, 1077, 1078, 1079, 1080, 1081, 1083, 1085], "branches": [[885, 886], [885, 889], [889, 890], [889, 897], [891, 892], [891, 895], [893, 891], [893, 894], [901, 903], [901, 1030], [903, 904], [903, 911], [904, 905], [904, 908], [906, 904], [906, 907], [911, 912], [911, 937], [913, 914], [913, 922], [924, 925], [924, 927], [929, 930], [929, 931], [939, 945], [939, 1062], [954, 955], [954, 989], [956, 957], [956, 981], [958, 959], [958, 960], [960, 961], [960, 962], [962, 963], [962, 964], [964, 965], [964, 966], [966, 967], [966, 970], [970, 971], [970, 972], [972, 973], [972, 975], [975, 976], [975, 978], [978, 956], [978, 979], [981, 982], [981, 989], [983, 984], [983, 986], [990, 992], [990, 1000], [1000, 1002], [1000, 1003], [1003, 1005], [1003, 1008], [1008, 1010], [1008, 1011], [1011, 1013], [1011, 1015], [1017, 1018], [1017, 1020], [1023, 1024], [1023, 1028], [1025, 1026], [1025, 1028], [1030, 1032], [1030, 1049], [1032, 1033], [1032, 1035], [1040, 1041], [1040, 1046], [1042, 1040], [1042, 1043], [1046, 1047], [1046, 1062], [1049, 1051], [1049, 1062], [1052, 1058], [1052, 1062], [1062, 1063], [1062, 1085], [1063, 1064], [1063, 1069], [1065, 1063], [1065, 1066], [1069, 1074], [1069, 1085], [1074, 1076], [1074, 1081], [1078, 1079], [1078, 1080], [1081, 1083], [1081, 1085]]}
# gained: {"lines": [885, 886, 889, 890, 891, 892, 893, 894, 895, 897, 898, 899, 901, 903, 911, 912, 913, 914, 915, 916, 917, 918, 920, 922, 924, 925, 926, 927, 928, 929, 931, 932, 934, 937, 938, 940, 941, 942, 943, 945, 948, 949, 950, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 970, 972, 975, 978, 979, 981, 982, 983, 986, 989, 990, 992, 996, 998, 1000, 1002, 1003, 1005, 1006, 1007, 1008, 1010, 1011, 1013, 1017, 1018, 1020, 1023, 1024, 1025, 1026, 1028, 1030, 1032, 1033, 1035, 1037, 1040, 1041, 1042, 1043, 1046, 1047, 1049, 1051, 1053, 1054, 1055, 1056, 1058, 1059, 1062, 1063, 1064, 1065, 1066, 1070, 1071, 1072, 1074, 1076, 1077, 1078, 1079, 1080, 1081, 1085], "branches": [[885, 886], [885, 889], [889, 890], [889, 897], [891, 892], [891, 895], [893, 894], [901, 903], [901, 1030], [903, 911], [911, 912], [911, 937], [913, 914], [924, 925], [929, 931], [939, 945], [939, 1062], [954, 955], [954, 989], [956, 957], [956, 981], [958, 959], [960, 961], [962, 963], [964, 965], [966, 967], [970, 972], [972, 975], [975, 978], [978, 979], [981, 982], [983, 986], [990, 992], [990, 1000], [1000, 1002], [1000, 1003], [1003, 1005], [1003, 1008], [1008, 1010], [1008, 1011], [1011, 1013], [1017, 1018], [1017, 1020], [1023, 1024], [1023, 1028], [1025, 1026], [1030, 1032], [1030, 1049], [1032, 1033], [1032, 1035], [1040, 1041], [1040, 1046], [1042, 1043], [1046, 1047], [1049, 1051], [1052, 1058], [1052, 1062], [1062, 1063], [1062, 1085], [1063, 1064], [1063, 1069], [1065, 1066], [1069, 1074], [1069, 1085], [1074, 1076], [1074, 1081], [1078, 1079], [1078, 1080], [1081, 1085]]}

import types
import pytest

from browser_use.dom.serializer.serializer import DOMTreeSerializer
from browser_use.dom.views import SimplifiedNode, NodeType


class FakeOriginal:
    def __init__(
        self,
        node_type=NodeType.ELEMENT_NODE,
        tag_name='div',
        backend_node_id=1,
        is_actually_scrollable=False,
        is_scrollable=False,
        should_show_scroll_info=False,
        _compound_children=None,
        shadow_root_type=None,
        node_value='',
        snapshot_node=None,
        is_visible=False,
        hidden_elements_info=None,
        has_hidden_content=False,
        attributes=None,
    ):
        # Basic node identity
        self.node_type = node_type
        self.tag_name = tag_name
        self.backend_node_id = backend_node_id
        self.node_value = node_value

        # Various flags and collections
        self._is_actually_scrollable = is_actually_scrollable
        self.is_scrollable = is_scrollable
        self.should_show_scroll_info = should_show_scroll_info
        self._compound_children = _compound_children or []
        self.shadow_root_type = shadow_root_type
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self.hidden_elements_info = hidden_elements_info or []
        self.has_hidden_content = has_hidden_content
        self.attributes = attributes or {}

        # Other fields that serializer/_build may reference
        self.node_id = 0
        self.target_id = None
        self.frame_id = None
        self.content_document = None
        self.shadow_roots = None
        self.parent_node = None
        self.children_nodes = []
        # ax_node with a properties attribute to satisfy _build_attributes_string
        self.ax_node = types.SimpleNamespace(properties=[])
        # snapshot-related minimal object if provided as truthy
        self.snapshot_node = snapshot_node
        self.has_js_click_listener = False
        self.uuid = "fake-uuid"
        self._compound_children = _compound_children or []
        self.hidden_elements_info = hidden_elements_info or []
        self.has_hidden_content = has_hidden_content

    def get_scroll_info_text(self):
        return "x:10 y:20"

    @property
    def is_actually_scrollable(self):
        return getattr(self, "_is_actually_scrollable", False)


def test_serialize_tree_none_and_excluded_child():
    # None should return empty string
    assert DOMTreeSerializer.serialize_tree(None, []) == ''

    # excluded_by_parent: node itself excluded but children processed
    child_orig = FakeOriginal(
        node_type=NodeType.TEXT_NODE,
        node_value='  visible text  ',
        snapshot_node=True,
        is_visible=True,
    )
    child = SimplifiedNode(original_node=child_orig, children=[])
    parent_orig = FakeOriginal(node_type=NodeType.ELEMENT_NODE)
    parent = SimplifiedNode(original_node=parent_orig, children=[child], excluded_by_parent=True)

    out = DOMTreeSerializer.serialize_tree(parent, [])
    # child text should be present trimmed
    assert 'visible text' in out
    # parent should not show tag name because excluded_by_parent skips rendering of the node itself
    assert '<' not in out


def test_serialize_tree_svg_shadow_and_interactive_markers():
    # child that indicates a closed shadow root
    shadow_child_orig = FakeOriginal(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='closed')
    shadow_child = SimplifiedNode(original_node=shadow_child_orig, children=[])

    svg_orig = FakeOriginal(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='svg',
        backend_node_id=123,
        attributes={},  # keep empty to avoid attribute string
    )
    svg_node = SimplifiedNode(
        original_node=svg_orig,
        children=[shadow_child],
        is_shadow_host=True,
        is_interactive=True,
        is_new=True,
    )

    out = DOMTreeSerializer.serialize_tree(svg_node, [])
    # Should include shadow closed prefix and interactive backend marker and collapsed SVG text
    assert '|SHADOW(closed)|' in out
    assert '[123]' in out or '123' in out
    assert '<svg' in out
    assert 'SVG content collapsed' in out


def test_serialize_tree_interactive_scroll_iframe_frame_and_compounds_and_hidden():
    include_attributes = []

    # Interactive node with compound components present
    comp_child_info = [
        {
            'name': 'vol',
            'role': 'slider',
            'valuemin': 0,
            'valuemax': 100,
            'valuenow': 75,
            'options_count': None,
            'first_options': [],
            'format_hint': None,
        }
    ]
    interactive_orig = FakeOriginal(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='button',
        backend_node_id=333,
        is_actually_scrollable=False,
        is_scrollable=False,
        should_show_scroll_info=True,
        _compound_children=comp_child_info,
        attributes={},
    )
    interactive = SimplifiedNode(original_node=interactive_orig, children=[], is_interactive=True, is_new=True, is_shadow_host=True)

    # Scroll-only non-interactive node
    scroll_orig = FakeOriginal(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='div',
        backend_node_id=444,
        is_actually_scrollable=False,
        is_scrollable=True,
        should_show_scroll_info=True,
        attributes={},
    )
    scroll_node = SimplifiedNode(original_node=scroll_orig, children=[], is_interactive=False)

    # Iframe with hidden_elements_info - should display hint lines
    iframe_hidden = [{'tag': 'a', 'text': 'Click me', 'pages': 2}]
    iframe_orig = FakeOriginal(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='iframe',
        backend_node_id=555,
        is_actually_scrollable=False,
        is_scrollable=False,
        should_show_scroll_info=False,
        hidden_elements_info=iframe_hidden,
        attributes={},
    )
    iframe_node = SimplifiedNode(original_node=iframe_orig, children=[], is_interactive=False)

    # Frame case
    frame_orig = FakeOriginal(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='frame',
        backend_node_id=666,
        attributes={},
    )
    frame_node = SimplifiedNode(original_node=frame_orig, children=[], is_interactive=False)

    parent_orig = FakeOriginal(node_type=NodeType.ELEMENT_NODE, tag_name='section', attributes={})
    parent = SimplifiedNode(original_node=parent_orig, children=[interactive, scroll_node, iframe_node, frame_node])

    out = DOMTreeSerializer.serialize_tree(parent, include_attributes)

    # Interactive compound info should be present
    assert 'compound_components=' in out
    # Interactive backend id shown with marker
    assert '[333]' in out or '333' in out
    # Scroll-only should show scroll element marker
    assert 'scroll element' in out
    # Iframe and frame markers present
    assert 'IFRAME' in out.upper() or 'IFRAME' in out
    assert 'FRAME' in out.upper() or 'FRAME' in out
    # Hidden elements hint included for iframe
    assert 'more elements below' in out or 'more content below' in out or 'Click me' in out


def test_serialize_tree_document_fragment_and_text_nodes_and_shadow_end():
    # Document fragment closed shadow with child text -> should show Closed Shadow, child, Shadow End
    text_child_orig = FakeOriginal(
        node_type=NodeType.TEXT_NODE,
        node_value='  hello world  ',
        snapshot_node=True,
        is_visible=True,
    )
    text_child = SimplifiedNode(original_node=text_child_orig, children=[])

    frag_orig = FakeOriginal(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='closed')
    frag_node = SimplifiedNode(original_node=frag_orig, children=[text_child])

    out = DOMTreeSerializer.serialize_tree(frag_node, [])
    assert 'Closed Shadow' in out
    assert 'hello world' in out
    assert 'Shadow End' in out

    # Open shadow variant
    frag_orig_open = FakeOriginal(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type=None)
    frag_open = SimplifiedNode(original_node=frag_orig_open, children=[text_child])
    out2 = DOMTreeSerializer.serialize_tree(frag_open, [])
    assert 'Open Shadow' in out2
    assert 'Shadow End' in out2


def test_text_node_visibility_edge_cases():
    # Text node too short or invisible -> should not be included
    short_text_orig = FakeOriginal(
        node_type=NodeType.TEXT_NODE,
        node_value='a',
        snapshot_node=True,
        is_visible=True,
    )
    short_text = SimplifiedNode(original_node=short_text_orig, children=[])
    assert DOMTreeSerializer.serialize_tree(short_text, []) == ''

    invisible_text_orig = FakeOriginal(
        node_type=NodeType.TEXT_NODE,
        node_value='  visible-ish  ',
        snapshot_node=None,
        is_visible=False,
    )
    invisible_text = SimplifiedNode(original_node=invisible_text_orig, children=[])
    assert DOMTreeSerializer.serialize_tree(invisible_text, []) == ''
