# file: browser_use/dom/serializer/html_serializer.py:27-170
# asked: {"lines": [37, 39, 40, 41, 42, 43, 44, 46, 48, 51, 52, 55, 56, 57, 58, 61, 63, 65, 66, 67, 70, 71, 74, 75, 77, 78, 80, 81, 82, 85, 86, 87, 88, 91, 94, 95, 96, 97, 100, 116, 117, 118, 120, 123, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 137, 138, 141, 142, 143, 144, 145, 148, 149, 150, 151, 154, 156, 158, 160, 161, 162, 164, 166, 170], "branches": [[37, 39], [37, 46], [40, 41], [40, 44], [42, 40], [42, 43], [46, 48], [46, 65], [55, 56], [55, 61], [57, 55], [57, 58], [65, 66], [65, 158], [70, 71], [70, 74], [74, 75], [74, 85], [77, 78], [77, 80], [81, 82], [81, 85], [85, 86], [85, 91], [87, 88], [87, 91], [94, 95], [94, 100], [96, 97], [96, 100], [116, 117], [116, 120], [123, 125], [123, 133], [125, 126], [125, 130], [126, 127], [126, 130], [128, 126], [128, 129], [133, 135], [133, 141], [135, 136], [135, 154], [137, 135], [137, 138], [141, 142], [141, 148], [142, 143], [142, 148], [144, 142], [144, 145], [148, 149], [148, 154], [150, 148], [150, 151], [158, 160], [158, 164], [160, 161], [160, 162], [164, 166], [164, 170]]}
# gained: {"lines": [37, 39, 40, 41, 42, 43, 44, 46, 48, 51, 52, 55, 56, 57, 58, 61, 63, 65, 66, 67, 70, 71, 74, 75, 77, 78, 80, 81, 82, 85, 86, 87, 88, 91, 94, 95, 96, 97, 100, 116, 117, 118, 120, 123, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 137, 138, 141, 148, 149, 150, 151, 154, 156, 158, 160, 161, 164, 166, 170], "branches": [[37, 39], [37, 46], [40, 41], [40, 44], [42, 43], [46, 48], [46, 65], [55, 56], [55, 61], [57, 58], [65, 66], [65, 158], [70, 71], [70, 74], [74, 75], [74, 85], [77, 78], [77, 80], [81, 82], [85, 86], [85, 91], [87, 88], [94, 95], [94, 100], [96, 97], [116, 117], [116, 120], [123, 125], [123, 133], [125, 126], [126, 127], [126, 130], [128, 129], [133, 135], [133, 141], [135, 136], [135, 154], [137, 138], [141, 148], [148, 149], [148, 154], [150, 151], [158, 160], [158, 164], [160, 161], [164, 166], [164, 170]]}

import types
import pytest

from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType


def make_node(
    *,
    node_type=NodeType.ELEMENT_NODE,
    tag_name="div",
    node_value="",
    attributes=None,
    children=None,
    children_nodes=None,
    children_and_shadow_roots=None,
    shadow_roots=None,
    shadow_root_type=None,
    content_document=None,
):
    """Create a lightweight fake EnhancedDOMTreeNode with required attributes for serialization."""
    if attributes is None:
        attributes = {}
    if children is None:
        children = []
    if children_nodes is None:
        children_nodes = []
    if children_and_shadow_roots is None:
        # Default for document nodes; if not provided just use children
        children_and_shadow_roots = children
    if shadow_roots is None:
        shadow_roots = []

    ns = types.SimpleNamespace()
    ns.node_type = node_type
    ns.tag_name = tag_name
    ns.node_value = node_value
    ns.attributes = attributes
    ns.children = children
    ns.children_nodes = children_nodes
    ns.children_and_shadow_roots = children_and_shadow_roots
    ns.shadow_roots = shadow_roots
    ns.shadow_root_type = shadow_root_type
    ns.content_document = content_document
    return ns


def test_document_and_text_and_basic_element_serialization():
    serializer = HTMLSerializer()

    # Text node with characters that need escaping
    text = make_node(node_type=NodeType.TEXT_NODE, node_value='a & <b>')
    # Child element containing the text
    div = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='div', attributes={'class': 'x'}, children=[text])
    # Document node that contains the div in children_and_shadow_roots
    document = make_node(node_type=NodeType.DOCUMENT_NODE, children_and_shadow_roots=[div])

    out = serializer.serialize(document)
    assert out == '<div class="x">a &amp; &lt;b&gt;</div>'


def test_document_fragment_shadowroot_and_template_lowercase():
    serializer = HTMLSerializer()

    # Inner text and span
    t = make_node(node_type=NodeType.TEXT_NODE, node_value='hello')
    span = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='span', children=[t])

    # Document fragment acting as a shadow root with explicit type
    frag = make_node(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='CLOSED', children=[span])

    out = serializer.serialize(frag)
    assert out == '<template shadowroot="closed"><span>hello</span></template>'


@pytest.mark.parametrize(
    "node",
    [
        make_node(node_type=NodeType.ELEMENT_NODE, tag_name='style'),  # non-content tag
        make_node(node_type=NodeType.ELEMENT_NODE, tag_name='script'),  # non-content tag
    ],
)
def test_non_content_elements_skip(node):
    serializer = HTMLSerializer()
    assert serializer.serialize(node) == ""


def test_code_tag_hidden_and_bpr_guid_and_img_data_url_skips():
    serializer = HTMLSerializer()
    # code with display:none in style
    code_hidden = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='code', attributes={'style': 'display:none'})
    assert serializer.serialize(code_hidden) == ""

    # code with id containing bpr-guid
    code_bpr = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='code', attributes={'id': 'my-bpr-guid-1'})
    assert serializer.serialize(code_bpr) == ""

    # img data URL skip
    img = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='img', attributes={'src': 'data:image/png;base64,AAA=='})
    assert serializer.serialize(img) == ""


def test_attribute_serialization_and_void_elements_and_href_behavior():
    # Default: extract_links=False -> href should be skipped, data-* skipped, empty attribute becomes boolean attribute
    s_default = HTMLSerializer(extract_links=False)
    a_node = make_node(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='a',
        attributes={'href': 'http://x', 'class': 'c', 'data-foo': 'bar', 'empty': ''},
        children=[],
    )
    out = s_default.serialize(a_node)
    # href and data-foo removed, empty becomes standalone attribute
    assert out == '<a class="c" empty></a>'

    # When extract_links=True href preserved and escaped
    s_links = HTMLSerializer(extract_links=True)
    a_node2 = make_node(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='a',
        attributes={'href': 'a"b\'c', 'title': 't&<>'},
        children=[],
    )
    out2 = s_links.serialize(a_node2)
    # Ensure proper escaping of attribute values
    assert out2 == '<a href="a&quot;b&#x27;c" title="t&amp;&lt;&gt;"></a>'

    # Void element (br) with attribute
    br = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='br', attributes={'id': 'x'})
    assert s_default.serialize(br) == '<br id="x" />'


def test_table_normalization_with_shadow_roots_and_thead_tbody():
    serializer = HTMLSerializer()

    # caption before rows
    caption_text = make_node(node_type=NodeType.TEXT_NODE, node_value='cap')
    caption = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='caption', children=[caption_text])

    # first tr with a th
    th_text = make_node(node_type=NodeType.TEXT_NODE, node_value='H1')
    th = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='th', children=[th_text])
    first_tr = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='tr', children=[th])

    # second tr with a td
    td_text = make_node(node_type=NodeType.TEXT_NODE, node_value='d1')
    td = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='td', children=[td_text])
    second_tr = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='tr', children=[td])

    # a shadow root to ensure serialization of shadow_roots ahead of table children
    shadow_text = make_node(node_type=NodeType.TEXT_NODE, node_value='s')
    shadow_span = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='span', children=[shadow_text])
    shadow_frag = make_node(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='open', children=[shadow_span])

    table = make_node(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='table',
        children=[caption, first_tr, second_tr],
        shadow_roots=[shadow_frag],
    )

    out = serializer.serialize(table)
    # Build expected pieces to assert presence and ordering
    assert out.startswith('<table>')
    # shadow root should come before thead/tbody
    assert '<template shadowroot="open"><span>s</span></template>' in out
    # caption present
    assert '<caption>cap</caption>' in out
    # thead wrapping first_tr
    assert '<thead>' in out and '</thead>' in out
    assert '<th>H1</th>' in out
    # tbody wrapping remaining rows
    assert '<tbody>' in out and '</tbody>' in out
    assert '<td>d1</td>' in out
    assert out.endswith('</table>')


def test_iframe_content_document_serialization():
    serializer = HTMLSerializer()

    # paragraph inside iframe content document
    p_text = make_node(node_type=NodeType.TEXT_NODE, node_value='ptext')
    p = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='p', children=[p_text])

    # Important: serializer looks at content_document.children_nodes for iframe serialization
    content_doc = make_node(node_type=NodeType.DOCUMENT_NODE, children_nodes=[p])
    iframe = make_node(node_type=NodeType.ELEMENT_NODE, tag_name='iframe', content_document=content_doc)

    out = serializer.serialize(iframe)
    # iframe tag should contain serialized content document children
    assert '<p>ptext</p>' in out
    assert out.startswith('<iframe>')
    assert out.endswith('</iframe>')


def test_comment_and_unknown_node_types_return_empty():
    serializer = HTMLSerializer()
    comment = make_node(node_type=NodeType.COMMENT_NODE)
    assert serializer.serialize(comment) == ""

    # Use a node type that's not explicitly handled (e.g., PROCESSING_INSTRUCTION_NODE)
    unknown = make_node(node_type=NodeType.PROCESSING_INSTRUCTION_NODE)
    assert serializer.serialize(unknown) == ""
