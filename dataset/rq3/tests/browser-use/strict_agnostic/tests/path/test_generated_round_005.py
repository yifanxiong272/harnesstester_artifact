import types
import pytest
from types import SimpleNamespace

from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType


def make_node(
    node_type,
    tag_name=None,
    attributes=None,
    children=None,
    children_and_shadow_roots=None,
    shadow_roots=None,
    content_document=None,
    shadow_root_type=None,
    node_value=None,
):
    """Create a lightweight fake node mimicking EnhancedDOMTreeNode for deterministic testing."""
    return SimpleNamespace(
        node_type=node_type,
        tag_name=tag_name,
        attributes=(attributes or {}) if attributes is not None else None,
        children=children or [],
        children_and_shadow_roots=children_and_shadow_roots or [],
        shadow_roots=shadow_roots or [],
        content_document=content_document,
        shadow_root_type=shadow_root_type,
        node_value=node_value,
        # some code paths access .children_nodes on content_document
        children_nodes=(getattr(content_document, 'children_nodes', None) if content_document else None),
    )


def test_document_and_children_round_005():
    """DOCUMENT_NODE should serialize all non-empty children and escape text nodes."""
    s = HTMLSerializer()

    # Text child that should be escaped
    text_child = make_node(NodeType.TEXT_NODE, node_value='a & b <c>')

    # Empty text child (node_value None) should produce '' and be skipped
    empty_text = make_node(NodeType.TEXT_NODE, node_value=None)

    doc = make_node(
        NodeType.DOCUMENT_NODE,
        children_and_shadow_roots=[text_child, empty_text],
    )

    out = s.serialize(doc)
    # Escaped text must appear, and empty_text must not contribute anything
    assert 'a &amp; b &lt;c&gt;' in out
    assert out.count('&lt;') == 1


def test_document_fragment_shadowroot_round_005():
    """DOCUMENT_FRAGMENT_NODE should wrap children in a template with shadowroot attribute."""
    s = HTMLSerializer()

    frag_text = make_node(NodeType.TEXT_NODE, node_value='shadowtext')
    frag = make_node(
        NodeType.DOCUMENT_FRAGMENT_NODE,
        children=[frag_text],
        shadow_root_type='CLOSED',
    )

    out = s.serialize(frag)
    # Should be wrapped in a template and contain the escaped inner text
    assert out.startswith('<template')
    assert 'shadowroot="closed"' in out
    assert 'shadowtext' in out
    assert out.endswith('</template>')


def test_element_skips_and_attrs_round_005():
    """Element skip rules (style/script/code/img base64) and attribute serialization/void elements."""
    s = HTMLSerializer()

    style_node = make_node(NodeType.ELEMENT_NODE, tag_name='style')
    assert s.serialize(style_node) == ''

    # code tag hidden via style
    code_hidden = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'style': 'display:none'},
    )
    assert s.serialize(code_hidden) == ''

    # code tag hidden via id pattern
    code_id = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'id': 'some-bpr-guid-value'},
    )
    assert s.serialize(code_id) == ''

    # img with base64 src should be skipped
    img_base64 = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='img',
        attributes={'src': 'data:image/png;base64,XXX'},
    )
    assert s.serialize(img_base64) == ''

    # Non-base64 img should produce a self-closing tag and include attributes
    img = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='img',
        attributes={'src': 'x.png', 'alt': 'ok'},
    )
    out = s.serialize(img)
    # Must be an img opening and self-closing ( /> at end) and include attributes
    assert out.startswith('<img')
    assert out.endswith(' />')
    assert 'src="x.png"' in out
    assert 'alt="ok"' in out


def test_element_shadow_roots_and_children_round_005():
    """Shadow roots are serialized before light DOM children and element tags wrap content."""
    s = HTMLSerializer()

    # Shadow root fragment with inner text 'S'
    sr_text = make_node(NodeType.TEXT_NODE, node_value='S')
    shadow_frag = make_node(NodeType.DOCUMENT_FRAGMENT_NODE, children=[sr_text], shadow_root_type='OPEN')

    # Light DOM child with inner text 'C'
    child_text = make_node(NodeType.TEXT_NODE, node_value='C')

    div = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='div',
        attributes={'class': 'x'},
        shadow_roots=[shadow_frag],
        children=[child_text],
    )

    out = s.serialize(div)
    # Should have a <div> ... </div> wrapper
    assert out.startswith('<div')
    assert out.endswith('</div>')
    # Shadow root content 'S' must appear before light DOM child 'C'
    assert out.count('S') == 1
    assert out.count('C') == 1
    assert out.index('S') < out.index('C')


def test_iframe_content_document_round_005():
    """iframe and frame tag handling: content_document children must be serialized into parent output."""
    s = HTMLSerializer()

    iframe_child = make_node(NodeType.TEXT_NODE, node_value='iframe inner')
    content_doc = SimpleNamespace(children_nodes=[iframe_child])

    iframe = make_node(
        NodeType.ELEMENT_NODE,
        tag_name='iframe',
        content_document=content_doc,
    )

    out = s.serialize(iframe)
    # The serialized iframe should contain the iframe child text (escaped)
    assert 'iframe inner' in out


def test_text_comment_unknown_round_005():
    """Text nodes are escaped, comment nodes and unknown types produce empty string."""
    s = HTMLSerializer()

    text = make_node(NodeType.TEXT_NODE, node_value='5 > 3 & ok')
    assert s.serialize(text) == s._escape_html('5 > 3 & ok')

    comment = make_node(NodeType.COMMENT_NODE)
    assert s.serialize(comment) == ''

    unknown = make_node(9999)  # an unknown node type
    assert s.serialize(unknown) == ''
