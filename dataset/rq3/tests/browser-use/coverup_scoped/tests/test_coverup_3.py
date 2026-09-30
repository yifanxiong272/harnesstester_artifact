# file: browser_use/dom/serializer/html_serializer.py:27-170
# asked: {"lines": [37, 39, 40, 41, 42, 43, 44, 46, 48, 51, 52, 55, 56, 57, 58, 61, 63, 65, 66, 67, 70, 71, 74, 75, 77, 78, 80, 81, 82, 85, 86, 87, 88, 91, 94, 95, 96, 97, 100, 116, 117, 118, 120, 123, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 137, 138, 141, 142, 143, 144, 145, 148, 149, 150, 151, 154, 156, 158, 160, 161, 162, 164, 166, 170], "branches": [[37, 39], [37, 46], [40, 41], [40, 44], [42, 40], [42, 43], [46, 48], [46, 65], [55, 56], [55, 61], [57, 55], [57, 58], [65, 66], [65, 158], [70, 71], [70, 74], [74, 75], [74, 85], [77, 78], [77, 80], [81, 82], [81, 85], [85, 86], [85, 91], [87, 88], [87, 91], [94, 95], [94, 100], [96, 97], [96, 100], [116, 117], [116, 120], [123, 125], [123, 133], [125, 126], [125, 130], [126, 127], [126, 130], [128, 126], [128, 129], [133, 135], [133, 141], [135, 136], [135, 154], [137, 135], [137, 138], [141, 142], [141, 148], [142, 143], [142, 148], [144, 142], [144, 145], [148, 149], [148, 154], [150, 148], [150, 151], [158, 160], [158, 164], [160, 161], [160, 162], [164, 166], [164, 170]]}
# gained: {"lines": [37, 39, 40, 41, 42, 43, 44, 46, 48, 51, 52, 55, 56, 57, 58, 61, 63, 65, 66, 67, 70, 71, 74, 75, 77, 78, 80, 81, 82, 85, 86, 87, 88, 91, 94, 95, 96, 97, 100, 116, 117, 118, 120, 123, 125, 126, 127, 128, 129, 130, 131, 133, 135, 136, 137, 138, 141, 142, 143, 144, 145, 148, 149, 150, 151, 154, 156, 158, 160, 161, 164, 166, 170], "branches": [[37, 39], [37, 46], [40, 41], [40, 44], [42, 43], [46, 48], [46, 65], [55, 56], [55, 61], [57, 58], [65, 66], [65, 158], [70, 71], [70, 74], [74, 75], [74, 85], [77, 78], [77, 80], [81, 82], [85, 86], [85, 91], [87, 88], [94, 95], [94, 100], [96, 97], [116, 117], [116, 120], [123, 125], [123, 133], [125, 126], [126, 127], [126, 130], [128, 129], [133, 135], [133, 141], [135, 136], [135, 154], [137, 138], [141, 142], [141, 148], [142, 143], [142, 148], [144, 145], [148, 149], [148, 154], [150, 151], [158, 160], [158, 164], [160, 161], [164, 166], [164, 170]]}

import pytest
from browser_use.dom.serializer.html_serializer import HTMLSerializer
from browser_use.dom.views import NodeType


class DummyNode:
    """
    Minimal duck-typed stand-in for EnhancedDOMTreeNode for testing HTMLSerializer.
    Only implements the attributes and properties that HTMLSerializer.serialize accesses.
    """

    def __init__(
        self,
        node_type,
        node_value="",
        tag_name="",
        attributes=None,
        children=None,
        shadow_roots=None,
        shadow_root_type=None,
        content_document=None,
        children_nodes=None,
        children_and_shadow_roots=None,
    ):
        self.node_type = node_type
        self.node_value = node_value
        # store tag_name as underlying attribute; serializer expects .tag_name property
        self._tag_name = tag_name or ""
        self.attributes = attributes or {}
        self._children = children or []
        self.shadow_roots = shadow_roots or []
        self.shadow_root_type = shadow_root_type
        self.content_document = content_document
        # some code references .children_nodes directly (for content_document)
        self.children_nodes = children_nodes or []
        # allow explicit override of children_and_shadow_roots list
        self._children_and_shadow_roots = children_and_shadow_roots

    @property
    def children(self):
        return self._children or []

    @property
    def children_and_shadow_roots(self):
        if self._children_and_shadow_roots is not None:
            return self._children_and_shadow_roots
        # default: shadow roots first (as some code expects) then children
        return list(self.shadow_roots or []) + list(self.children or [])

    @property
    def tag_name(self):
        return self._tag_name

    def __repr__(self):
        return f"<DummyNode {self.node_type} tag={self._tag_name!r} value={self.node_value!r}>"


def make_text(text):
    return DummyNode(node_type=NodeType.TEXT_NODE, node_value=text)


def make_comment(text="c"):
    return DummyNode(node_type=NodeType.COMMENT_NODE, node_value=text)


def make_element(tag, attributes=None, children=None, shadow_roots=None, shadow_root_type=None, content_document=None):
    return DummyNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name=tag,
        attributes=attributes or {},
        children=children or [],
        shadow_roots=shadow_roots or [],
        shadow_root_type=shadow_root_type,
        content_document=content_document,
    )


def make_document(children_and_shadow_roots=None):
    return DummyNode(node_type=NodeType.DOCUMENT_NODE, children_and_shadow_roots=children_and_shadow_roots)


def make_fragment(children=None, shadow_root_type=None):
    return DummyNode(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, children=children or [], shadow_root_type=shadow_root_type)


def make_unknown():
    # Create a node with a type not covered: use an integer sentinel or a NodeType not matched
    class FakeType:
        pass
    return DummyNode(node_type=FakeType(), node_value="unknown")


def test_document_and_text_serialization_combination():
    s = HTMLSerializer()
    # Text node should be escaped
    t1 = make_text("Hello & <world>")
    # A span element with a child text node
    span = make_element("span", attributes={"class": "x"}, children=[make_text("child")])
    # Document node with children_and_shadow_roots that includes t1 and span
    doc = make_document(children_and_shadow_roots=[t1, span])
    html = s.serialize(doc)
    # Ensure both text and the span are present and escaping applied
    assert "Hello &amp; &lt;world&gt;" in html
    assert html.count("<span") == 1 and html.endswith("</span>"), "expected span element to be serialized with closing tag"


def test_document_fragment_creates_template_and_serializes_children():
    s = HTMLSerializer()
    # fragment containing a text node -> should wrap in <template shadowroot="open"> ... </template>
    frag = make_fragment(children=[make_text("fragtext")], shadow_root_type=None)
    out = s.serialize(frag)
    assert out.startswith('<template shadowroot="open">')
    assert "fragtext" in out
    assert out.endswith("</template>")


def test_element_skips_certain_tags_and_code_hidden_and_ids_and_img_dataurl():
    s = HTMLSerializer()

    # script (and other blacklisted tags) should produce empty string
    script = make_element("script", children=[make_text("alert(1)")])
    assert s.serialize(script) == ""

    # code with display:none style should be skipped
    code_hidden = make_element("code", attributes={"style": "display:none"})
    assert s.serialize(code_hidden) == ""

    # code with bpr-guid like id should be skipped
    code_bpr = make_element("code", attributes={"id": "foo-bpr-guid-123"})
    assert s.serialize(code_bpr) == ""

    # img with base64 src should be skipped
    img = make_element("img", attributes={"src": "data:image/png;base64,AAA"})
    assert s.serialize(img) == ""


def test_void_element_serialization_and_attributes_and_closing_tags(monkeypatch):
    # Test a void element like <br /> and a normal element with attributes + children.
    s = HTMLSerializer(extract_links=True)

    br = make_element("br")
    assert s.serialize(br) == "<br />"

    # Normal div with attributes and a child text node:
    div = make_element("div", attributes={"title": 'a "b" & c'}, children=[make_text("X")])
    out = s.serialize(div)
    assert out.startswith("<div")
    assert out.endswith("</div>")
    assert "X" in out
    # attribute should be present (serializer should escape/quote attribute value)
    assert "title" in out


def test_table_and_shadow_roots_and_table_children_monkeypatched(monkeypatch):
    s = HTMLSerializer()
    # Create a shadow root fragment that will be serialized inside table
    shadow = make_fragment(children=[make_text("inside-shadow")], shadow_root_type="closed")
    # Table node with a shadow root and some children (children content will be produced by _serialize_table_children)
    table = make_element("table", shadow_roots=[shadow], children=[make_element("tbody")])

    # Monkeypatch the _serialize_table_children to ensure that branch executes predictably
    monkeypatch.setattr(
        s,
        "_serialize_table_children",
        lambda table_node, depth: "<tbody><tr><td>DATA</td></tr></tbody>",
    )

    out = s.serialize(table)
    # Should contain the serialized shadow root template and our monkeypatched tbody
    assert '<template shadowroot="closed">' in out
    assert "<tbody><tr><td>DATA</td></tr></tbody>" in out
    assert out.endswith("</table>")


def test_iframe_content_document_children_serialized():
    s = HTMLSerializer()
    # content document with children_nodes list
    cd_child = make_element("p", children=[make_text("inframe")])
    content_doc = DummyNode(node_type=NodeType.DOCUMENT_NODE, children_nodes=[cd_child])
    iframe = make_element("iframe", content_document=content_doc)
    out = s.serialize(iframe)
    # The iframe content child should be serialized inside the iframe
    assert "inframe" in out


def test_shadow_roots_then_light_dom_children_order():
    s = HTMLSerializer()
    # Shadow root with identifiable content
    sr = make_fragment(children=[make_text("S")], shadow_root_type="open")
    # light DOM child
    ld = make_element("span", children=[make_text("L")])
    host = make_element("div", shadow_roots=[sr], children=[ld])
    out = s.serialize(host)
    # Shadow root content (template) should appear before light DOM child content
    assert out.index("S") < out.index("L")
    # and tags present
    assert out.startswith("<div")
    assert out.endswith("</div>")


def test_text_and_comment_and_unknown_node_types():
    s = HTMLSerializer()
    txt = make_text("1 < 2 & 3")
    assert "&lt;" in s.serialize(txt) and "&amp;" in s.serialize(txt)

    com = make_comment("a comment")
    # comments should be skipped
    assert s.serialize(com) == ""

    unk = make_unknown()
    # unknown node type path should return empty string
    assert s.serialize(unk) == ""
