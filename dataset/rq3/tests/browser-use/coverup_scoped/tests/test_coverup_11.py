# file: browser_use/dom/serializer/html_serializer.py:172-246
# asked: {"lines": [178, 179, 180, 183, 184, 185, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 200, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213, 214, 215, 218, 221, 222, 223, 224, 227, 228, 229, 232, 233, 234, 235, 236, 237, 238, 239, 241, 242, 243, 244, 246], "branches": [[179, 180], [179, 183], [187, 189], [187, 197], [190, 191], [190, 194], [192, 190], [192, 193], [199, 200], [199, 208], [200, 199], [200, 202], [203, 204], [203, 206], [208, 210], [208, 218], [211, 212], [211, 215], [213, 211], [213, 214], [221, 222], [221, 227], [223, 221], [223, 224], [233, 234], [233, 241], [235, 236], [235, 239], [237, 235], [237, 238], [241, 242], [241, 246], [243, 241], [243, 244]]}
# gained: {"lines": [178, 179, 180, 183, 184, 185, 187, 189, 190, 191, 192, 193, 194, 197, 198, 199, 200, 202, 203, 204, 205, 206, 208, 210, 211, 212, 213, 214, 215, 218, 221, 222, 223, 224, 227, 228, 229, 232, 233, 234, 235, 236, 237, 238, 239, 241, 242, 243, 244, 246], "branches": [[179, 180], [179, 183], [187, 189], [187, 197], [190, 191], [190, 194], [192, 193], [199, 200], [200, 199], [200, 202], [203, 204], [203, 206], [208, 210], [208, 218], [211, 212], [211, 215], [213, 214], [221, 222], [221, 227], [223, 224], [233, 234], [233, 241], [235, 236], [235, 239], [237, 238], [241, 242], [241, 246], [243, 244]]}

import pytest

from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType


class FakeNode:
    def __init__(self, tag_name=None, node_type=NodeType.ELEMENT_NODE, children=None):
        self.tag_name = tag_name
        self.node_type = node_type
        # ensure list copy semantics
        self.children = list(children) if children else []


def _make_serializer_stub(monkeypatch, record):
    """
    Replace HTMLSerializer.serialize with a stub that records calls and returns
    a predictable string based on node.tag_name and depth.
    """
    def fake_serialize(self, node, depth):
        tag = getattr(node, "tag_name", None)
        record.append((tag, depth))
        # Represent text nodes or nodes lacking tag_name as 'None'
        return f"[{tag}@{depth}]"
    monkeypatch.setattr(HTMLSerializer, "serialize", fake_serialize)


def test_empty_children_returns_empty():
    table = FakeNode(tag_name="table", children=[])
    serializer = HTMLSerializer()
    assert serializer._serialize_table_children(table, 0) == ""


def test_has_thead_serializes_children_with_depth_plus_one(monkeypatch):
    # Table with explicit thead present
    thead = FakeNode(tag_name="thead")
    tbody = FakeNode(tag_name="tbody")
    table = FakeNode(tag_name="table", children=[thead, tbody])

    calls = []
    _make_serializer_stub(monkeypatch, calls)

    serializer = HTMLSerializer()
    res = serializer._serialize_table_children(table, 3)

    # Each child should be serialized at depth+1 (3+1=4)
    assert res == "[thead@4][tbody@4]"
    assert calls == [("thead", 4), ("tbody", 4)]


def test_no_header_row_serializes_normally_when_first_tr_has_no_th(monkeypatch):
    # First <tr> has no <th>; should trigger "no header row detected" branch
    tr_without_th = FakeNode(tag_name="tr", children=[FakeNode(tag_name="td")])
    another = FakeNode(tag_name="colgroup")
    table = FakeNode(tag_name="table", children=[tr_without_th, another])

    calls = []
    _make_serializer_stub(monkeypatch, calls)

    serializer = HTMLSerializer()
    res = serializer._serialize_table_children(table, 1)

    # Should serialize each child at depth+1 (1+1=2)
    assert res == "[tr@2][colgroup@2]"
    assert calls == [("tr", 2), ("colgroup", 2)]


def test_header_row_wraps_thead_and_wraps_remaining_in_tbody(monkeypatch):
    # Children before header (e.g., caption), header tr contains <th>, then remaining rows
    caption = FakeNode(tag_name="caption")
    header_tr = FakeNode(tag_name="tr", children=[FakeNode(tag_name="th"), FakeNode(tag_name="th")])
    row1 = FakeNode(tag_name="tr", children=[FakeNode(tag_name="td")])
    row2 = FakeNode(tag_name="tr", children=[FakeNode(tag_name="td")])
    table = FakeNode(tag_name="table", children=[caption, header_tr, row1, row2])

    calls = []
    _make_serializer_stub(monkeypatch, calls)

    serializer = HTMLSerializer()
    res = serializer._serialize_table_children(table, 0)

    # Expect: caption serialized at depth+1 (1), then <thead>, header serialized at depth+2 (2), </thead>,
    # then <tbody>, remaining serialized at depth+2 (2), </tbody>
    expected = "[caption@1]" + "<thead>" + "[tr@2]" + "</thead>" + "<tbody>" + "[tr@2]" + "[tr@2]" + "</tbody>"
    assert res == expected

    # Verify the serialize calls and depths: caption at 1, header at 2, then two remaining rows at 2 each
    assert calls == [("caption", 1), ("tr", 2), ("tr", 2), ("tr", 2)]


def test_header_row_with_existing_tbody_serializes_remaining_at_depth_plus_one(monkeypatch):
    # There is a <tbody> sibling present; remaining rows should be serialized at depth+1 (not wrapped)
    header_tr = FakeNode(tag_name="tr", children=[FakeNode(tag_name="th")])
    tbody = FakeNode(tag_name="tbody", children=[FakeNode(tag_name="tr", children=[FakeNode(tag_name="td")])])
    other = FakeNode(tag_name="tfoot")
    # Put tbody after header so it is included in remaining; has_tbody should be True
    table = FakeNode(tag_name="table", children=[header_tr, tbody, other])

    calls = []
    _make_serializer_stub(monkeypatch, calls)

    serializer = HTMLSerializer()
    res = serializer._serialize_table_children(table, 2)

    # Expected: <thead>, header serialized at depth+2 (4), </thead>,
    # then remaining serialized at depth+1 (3) because has_tbody True triggers else branch
    # Note: children before header (none) so no extra prefix
    expected = "<thead>" + "[tr@4]" + "</thead>" + "[tbody@3]" + "[tfoot@3]"
    assert res == expected

    assert calls == [("tr", 4), ("tbody", 3), ("tfoot", 3)]
