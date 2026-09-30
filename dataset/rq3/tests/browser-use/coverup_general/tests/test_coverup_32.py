# file: browser_use/dom/serializer/html_serializer.py:172-246
# asked: {"lines": [178, 179, 180, 183, 184, 185, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 200, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213, 214, 215, 218, 221, 222, 223, 224, 227, 228, 229, 232, 233, 234, 235, 236, 237, 238, 239, 241, 242, 243, 244, 246], "branches": [[179, 180], [179, 183], [187, 189], [187, 197], [190, 191], [190, 194], [192, 190], [192, 193], [199, 200], [199, 208], [200, 199], [200, 202], [203, 204], [203, 206], [208, 210], [208, 218], [211, 212], [211, 215], [213, 211], [213, 214], [221, 222], [221, 227], [223, 221], [223, 224], [233, 234], [233, 241], [235, 236], [235, 239], [237, 235], [237, 238], [241, 242], [241, 246], [243, 241], [243, 244]]}
# gained: {"lines": [178, 179, 180, 183, 184, 185, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 200, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213, 214, 215, 218, 221, 222, 223, 224, 227, 228, 229, 232, 233, 234, 235, 236, 237, 238, 239, 241, 242, 243, 244, 246], "branches": [[179, 180], [179, 183], [187, 189], [187, 197], [190, 191], [190, 194], [192, 193], [199, 200], [199, 208], [200, 199], [200, 202], [203, 204], [208, 210], [208, 218], [211, 212], [211, 215], [213, 214], [221, 222], [221, 227], [223, 224], [233, 234], [233, 241], [235, 236], [235, 239], [237, 238], [241, 242], [241, 246], [243, 244]]}

import pytest

from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import EnhancedDOMTreeNode, NodeType


def make_node(tag, children=None, node_id=1):
    # Helper to construct an EnhancedDOMTreeNode with minimal required fields.
    if children is None:
        children = []
    return EnhancedDOMTreeNode(
        node_id=node_id,
        backend_node_id=0,
        node_type=NodeType.ELEMENT_NODE,
        node_name=tag,
        node_value='',
        attributes={},
        is_scrollable=None,
        is_visible=None,
        absolute_position=None,
        target_id=None,
        frame_id=None,
        session_id=None,
        content_document=None,
        shadow_root_type=None,
        shadow_roots=None,
        parent_node=None,
        children_nodes=children,
        ax_node=None,
        snapshot_node=None,
    )


def test_serialize_table_children_empty():
    serializer = HTMLSerializer()
    table = make_node('table', children=[])
    # Empty children should return empty string
    out = serializer._serialize_table_children(table, depth=0)
    assert out == ''


def test_serialize_table_children_with_thead(monkeypatch):
    serializer = HTMLSerializer()
    # Create a thead and tbody child
    thead = make_node('thead')
    tbody = make_node('tbody')
    table = make_node('table', children=[thead, tbody])

    # Monkeypatch serializer.serialize to a predictable string using node.tag_name
    # The function is assigned to the instance and will be called as serializer.serialize(child, depth)
    serializer.serialize = lambda node, depth=0: f"S{node.tag_name}:{depth}"

    out = serializer._serialize_table_children(table, depth=0)
    # Since has_thead is True, each child gets serialized at depth+1
    assert out == "Sthead:1Stbody:1"


def test_serialize_table_children_no_tr_serializes_normally(monkeypatch):
    serializer = HTMLSerializer()
    # Create children without any <tr>
    colgroup = make_node('colgroup')
    caption = make_node('caption')
    table = make_node('table', children=[colgroup, caption])

    serializer.serialize = lambda node, depth=0: f"S{node.tag_name}:{depth}"

    out = serializer._serialize_table_children(table, depth=2)
    # No thead and no tr with th -> serialize normally at depth+1
    assert out == "Scolgroup:3Scaption:3"


def test_serialize_table_children_wraps_thead_and_adds_tbody_when_no_tbody(monkeypatch):
    serializer = HTMLSerializer()
    # child before header (e.g., caption)
    caption = make_node('caption')
    # first tr contains a th -> should be wrapped in thead
    th = make_node('th')
    first_tr = make_node('tr', children=[th])
    # remaining rows
    tr2 = make_node('tr')
    tr3 = make_node('tr')
    table = make_node('table', children=[caption, first_tr, tr2, tr3])

    # Serialize returns tag and depth for verification
    serializer.serialize = lambda node, depth=0: f"S{node.tag_name}:{depth}"

    out = serializer._serialize_table_children(table, depth=0)
    # Expected:
    # - caption serialized at depth+1 -> 1
    # - <thead> literal
    # - first_tr serialized at depth+2 -> 2
    # - </thead>
    # - <tbody> wrapper
    # - remaining trs serialized at depth+2 -> 2 each
    # - </tbody>
    expected = (
        "Scaption:1"
        "<thead>"
        "Str:2"
        "</thead>"
        "<tbody>"
        "Str:2"
        "Str:2"
        "</tbody>"
    )
    assert out == expected


def test_serialize_table_children_with_existing_tbody_uses_else_branch(monkeypatch):
    serializer = HTMLSerializer()
    # first tr contains a th -> header detected
    th = make_node('th')
    first_tr = make_node('tr', children=[th])
    # remaining includes an existing tbody element; has_tbody should be True
    tbody = make_node('tbody')
    tr_after = make_node('tr')
    table = make_node('table', children=[first_tr, tbody, tr_after])

    # Serialize returns tag and depth for verification
    serializer.serialize = lambda node, depth=0: f"S{node.tag_name}:{depth}"

    out = serializer._serialize_table_children(table, depth=1)
    # Because has_tbody is True, the remaining children after the first_tr
    # should be serialized at depth+1 (not wrapped in a new <tbody> and not depth+2)
    # Also the first_tr should be wrapped in <thead> and serialized at depth+2
    expected = (
        "<thead>"
        "Str:3"  # first_tr at depth+2 -> 3
        "</thead>"
        # remaining serialized at depth+1 -> 2
        "Stbody:2"
        "Str:2"
    )
    assert out == expected
