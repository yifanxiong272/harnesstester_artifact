import types
from types import SimpleNamespace

import pytest

from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType


def test_document_and_text_node_round_005():
    """DOCUMENT_NODE should serialize children_and_shadow_roots, skipping comments and escaping text."""
    s = HTMLSerializer(False)

    text_child = SimpleNamespace(
        node_type=NodeType.TEXT_NODE,
        node_value='<&>',
    )
    comment_child = SimpleNamespace(
        node_type=NodeType.COMMENT_NODE,
        node_value='should be ignored',
    )

    doc = SimpleNamespace(
        node_type=NodeType.DOCUMENT_NODE,
        # serializer looks for attribute `children_and_shadow_roots`
        children_and_shadow_roots=[text_child, comment_child],
    )

    out = s.serialize(doc)
    # use the serializer's own escape to avoid coupling to a concrete escape map
    assert out == s._escape_html('<&>')


def test_document_fragment_and_element_skips_round_005():
    """DOCUMENT_FRAGMENT_NODE should wrap children in a template and ELEMENT_NODE skips work (code/img/script)."""
    s = HTMLSerializer(False)

    # simple element child that will produce an opening and closing tag
    div_child = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='div',
        attributes={},
        # serializer accesses .children (light DOM) and .shadow_roots elsewhere
        children=[],
        shadow_roots=None,
        content_document=None,
    )

    fragment = SimpleNamespace(
        node_type=NodeType.DOCUMENT_FRAGMENT_NODE,
        shadow_root_type='CLOSED',
        children=[div_child],
    )

    out = s.serialize(fragment)
    assert out.startswith('<template shadowroot="closed">')
    assert '<div' in out and '</div>' in out
    assert out.endswith('</template>')

    # ELEMENT_NODE skip: script tag
    script = SimpleNamespace(node_type=NodeType.ELEMENT_NODE, tag_name='script', attributes=None)
    assert s.serialize(script) == ''

    # code tag with display:none style should be skipped
    code_hidden = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'style': 'display:none'},
        children=[],
        shadow_roots=None,
        content_document=None,
    )
    assert s.serialize(code_hidden) == ''

    # code tag with bpr-guid-like id should be skipped
    code_bpr = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'id': 'some-bpr-guid-123'},
        children=[],
        shadow_roots=None,
        content_document=None,
    )
    assert s.serialize(code_bpr) == ''

    # img with base64 data URI should be skipped
    img_data = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='img',
        attributes={'src': 'data:image/png;base64,AAAA'},
        children=[],
        shadow_roots=None,
        content_document=None,
    )
    assert s.serialize(img_data) == ''

    # img as a void element but not a data URI should render a self-closing tag and include attributes
    img = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='img',
        attributes={'alt': 'x', 'src': '/img.png'},
        children=[],
        shadow_roots=None,
        content_document=None,
    )
    out_img = s.serialize(img)
    assert out_img.startswith('<img')
    assert out_img.endswith(' />')
    # attributes should be present in the serialized output (order not asserted)
    assert 'alt' in out_img and 'src' in out_img


def test_table_shadowroots_and_iframe_content_round_005():
    """Table path should call _serialize_table_children; iframe should serialize its content_document children."""
    s = HTMLSerializer(False)

    # Patch _serialize_table_children to a deterministic value to assert table flow
    s._serialize_table_children = lambda node, depth: '<tbody><tr><td>cell</td></tr></tbody>'

    # create a shadow root that will be serialized first from table.shadow_roots
    shadow_child = SimpleNamespace(
        node_type=NodeType.DOCUMENT_FRAGMENT_NODE,
        shadow_root_type=None,
        children=[],
    )
    table_node = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='table',
        attributes={},
        shadow_roots=[shadow_child],
        children=[],
        content_document=None,
    )

    out_table = s.serialize(table_node)
    assert '<tbody>' in out_table and '</table>' in out_table
    assert '<tbody><tr><td>cell</td></tr></tbody>' in out_table

    # iframe with content_document children should serialize those children
    text_child = SimpleNamespace(node_type=NodeType.TEXT_NODE, node_value='frame-text')
    iframe_content_doc = SimpleNamespace(children_nodes=[text_child])
    iframe_node = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='iframe',
        attributes={},
        content_document=iframe_content_doc,
        children=[],
        shadow_roots=None,
    )

    out_iframe = s.serialize(iframe_node)
    # text is included via the content_document traversal and should be escaped using the same escape function
    assert s._escape_html('frame-text') in out_iframe


def test_unknown_node_types_and_text_empty_round_005():
    """Unknown node types and empty TEXT_NODE values should return empty string."""
    s = HTMLSerializer(False)

    unknown = SimpleNamespace(node_type=9999)  # some unknown numeric node type
    assert s.serialize(unknown) == ''

    empty_text = SimpleNamespace(node_type=NodeType.TEXT_NODE, node_value='')
    assert s.serialize(empty_text) == ''
