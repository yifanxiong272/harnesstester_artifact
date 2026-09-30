import types
import pytest
from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType

# Helper to build lightweight node objects compatible with HTMLSerializer expectations
def make_node(tag_name=None, node_type=NodeType.ELEMENT_NODE, children=None):
    return types.SimpleNamespace(tag_name=tag_name, node_type=node_type, children=(children or []))


def test_empty_children_round_021():
    # Table node with no children should return an empty string
    ser = HTMLSerializer(extract_links=False)
    table = make_node(tag_name='table', children=[])

    out = ser._serialize_table_children(table, depth=0)
    assert out == ''


def test_has_thead_skips_normalization_round_021():
    # If the table already has a thead element, the function serializes children directly
    ser = HTMLSerializer(extract_links=False)

    thead = make_node(tag_name='thead', node_type=NodeType.ELEMENT_NODE)
    # non-element node: should be skipped by our serialize stub (returns empty)
    text_node = make_node(tag_name=None, node_type=object())

    table = make_node(tag_name='table', children=[thead, text_node])

    # Monkeypatch serialize to return a predictable token depending on tag_name
    def fake_serialize(child, depth):
        return f'[{child.tag_name}]' if getattr(child, 'tag_name', None) else ''

    ser.serialize = fake_serialize

    out = ser._serialize_table_children(table, depth=0)
    # Only the thead child produces non-empty serialization
    assert out == '[thead]'


def test_first_tr_header_and_tbody_wrap_round_021():
    # Ensure first <tr> with <th> is wrapped in <thead> and remaining <tr>s are wrapped in <tbody>
    ser = HTMLSerializer(extract_links=False)

    # Pre-header child (e.g., colgroup)
    colgroup = make_node(tag_name='colgroup')

    # Header tr (contains a th child)
    th_child = make_node(tag_name='th')
    header_tr = make_node(tag_name='tr', children=[th_child])

    # Two remaining rows
    row1 = make_node(tag_name='tr')
    row2 = make_node(tag_name='tr')

    table = make_node(tag_name='table', children=[colgroup, header_tr, row1, row2])

    # Deterministic serialization that encodes tag_name and depth
    def fake_serialize(child, depth):
        name = getattr(child, 'tag_name', None)
        return f'<{name}:{depth}>' if name is not None else ''

    ser.serialize = fake_serialize

    out = ser._serialize_table_children(table, depth=0)

    # Expected sequence:
    # - colgroup serialized at depth 1
    # - <thead>
    # - header_tr serialized at depth 2
    # - </thead>
    # - <tbody>
    # - remaining rows serialized at depth 2
    # - </tbody>
    expected = (
        '<colgroup:1>'
        '<thead>'
        '<tr:2>'
        '</thead>'
        '<tbody>'
        '<tr:2>'
        '<tr:2>'
        '</tbody>'
    )
    assert out == expected


def test_existing_tbody_keeps_remaining_serialization_round_021():
    # If the table already has a tbody child, remaining rows should be serialized as-is (no extra <tbody> wrapper)
    ser = HTMLSerializer(extract_links=False)

    # Header tr with th
    header_tr = make_node(tag_name='tr', children=[make_node(tag_name='th')])
    # Already-present tbody element
    existing_tbody = make_node(tag_name='tbody')

    table = make_node(tag_name='table', children=[header_tr, existing_tbody])

    def fake_serialize(child, depth):
        name = getattr(child, 'tag_name', None)
        return f'<{name}:{depth}>' if name is not None else ''

    ser.serialize = fake_serialize

    out = ser._serialize_table_children(table, depth=0)

    # Expected: <thead> with header_tr at depth 2, then existing tbody serialized at depth 1 (no extra wrappers)
    assert out == '<thead><tr:2></thead><tbody:1>'


def test_no_header_row_serialize_normally_round_021():
    # If no <tr> contains <th>, the rows are serialized normally (no thead/tbody changes)
    ser = HTMLSerializer(extract_links=False)

    tr1 = make_node(tag_name='tr', children=[make_node(tag_name='td')])
    tr2 = make_node(tag_name='tr', children=[make_node(tag_name='td')])

    table = make_node(tag_name='table', children=[tr1, tr2])

    def fake_serialize(child, depth):
        name = getattr(child, 'tag_name', None)
        return f'({name}:{depth})' if name is not None else ''

    ser.serialize = fake_serialize

    out = ser._serialize_table_children(table, depth=0)

    # Each child should be serialized at depth+1
    assert out == '(tr:1)(tr:1)'
