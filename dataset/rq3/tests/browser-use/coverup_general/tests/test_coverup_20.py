# file: browser_use/dom/serializer/eval_serializer.py:115-231
# asked: {"lines": [115, 116, 126, 127, 130, 131, 134, 135, 137, 138, 140, 141, 142, 145, 148, 149, 152, 153, 157, 158, 160, 161, 162, 163, 164, 165, 166, 167, 170, 171, 174, 177, 178, 179, 180, 183, 185, 186, 188, 190, 191, 194, 195, 196, 197, 200, 204, 206, 207, 209, 211, 214, 215, 216, 217, 219, 221, 223, 225, 226, 227, 228, 229, 231], "branches": [[126, 127], [126, 130], [130, 131], [130, 134], [134, 135], [134, 137], [140, 141], [140, 219], [148, 149], [148, 152], [152, 153], [152, 157], [157, 158], [157, 170], [160, 161], [160, 162], [164, 165], [164, 166], [170, 171], [170, 174], [185, 186], [185, 188], [190, 191], [190, 194], [194, 195], [194, 200], [196, 197], [196, 200], [206, 207], [206, 209], [214, 215], [214, 231], [216, 217], [216, 231], [219, 221], [219, 223], [223, 225], [223, 231], [225, 226], [225, 231], [228, 229], [228, 231]]}
# gained: {"lines": [115, 116, 126, 127, 130, 131, 134, 135, 137, 138, 140, 141, 142, 145, 148, 149, 152, 153, 157, 158, 160, 161, 162, 163, 164, 165, 166, 167, 170, 171, 174, 177, 178, 179, 180, 183, 185, 186, 188, 190, 191, 194, 195, 196, 197, 200, 204, 206, 207, 209, 211, 214, 215, 216, 217, 219, 221, 223, 225, 226, 227, 228, 229, 231], "branches": [[126, 127], [126, 130], [130, 131], [130, 134], [134, 135], [134, 137], [140, 141], [140, 219], [148, 149], [148, 152], [152, 153], [152, 157], [157, 158], [157, 170], [160, 161], [164, 165], [170, 171], [170, 174], [185, 186], [185, 188], [190, 191], [190, 194], [194, 195], [194, 200], [196, 197], [206, 207], [206, 209], [214, 215], [214, 231], [216, 217], [219, 221], [219, 223], [223, 225], [225, 226], [228, 229]]}

import types
import pytest

from browser_use.dom.serializer import eval_serializer as es


class FakeNodeType:
    ELEMENT_NODE = 1
    TEXT_NODE = 2
    DOCUMENT_FRAGMENT_NODE = 3


class FakeOriginalNode:
    def __init__(
        self,
        tag_name="div",
        node_type=FakeNodeType.ELEMENT_NODE,
        snapshot_node=True,
        is_visible=True,
        backend_node_id=1,
        should_show_scroll_info=False,
        scroll_text=None,
    ):
        self.tag_name = tag_name
        self.node_type = node_type
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self.backend_node_id = backend_node_id
        self.should_show_scroll_info = should_show_scroll_info
        self._scroll_text = scroll_text
        # Ensure attributes exists to match real objects expected by _build_compact_attributes
        self.attributes = {}

    def get_scroll_info_text(self):
        return self._scroll_text


class FakeSimplifiedNode:
    def __init__(
        self,
        original_node: FakeOriginalNode,
        children=None,
        is_interactive=False,
        should_display=True,
        excluded_by_parent=False,
    ):
        self.original_node = original_node
        self.children = children or []
        self.is_interactive = is_interactive
        self.should_display = should_display
        # sometimes serialize_tree checks hasattr(node, 'excluded_by_parent')
        if excluded_by_parent:
            self.excluded_by_parent = True


def make_node(
    tag="div",
    node_type=FakeNodeType.ELEMENT_NODE,
    snapshot_node=True,
    is_visible=True,
    backend_node_id=1,
    should_show_scroll_info=False,
    scroll_text=None,
    children=None,
    is_interactive=False,
    should_display=True,
    excluded_by_parent=False,
):
    orig = FakeOriginalNode(
        tag_name=tag,
        node_type=node_type,
        snapshot_node=snapshot_node,
        is_visible=is_visible,
        backend_node_id=backend_node_id,
        should_show_scroll_info=should_show_scroll_info,
        scroll_text=scroll_text,
    )
    return FakeSimplifiedNode(
        original_node=orig,
        children=children,
        is_interactive=is_interactive,
        should_display=should_display,
        excluded_by_parent=excluded_by_parent,
    )


@pytest.fixture(autouse=True)
def patch_module_consts(monkeypatch):
    # Patch NodeType and sets used inside the module
    monkeypatch.setattr(es, "NodeType", FakeNodeType)
    monkeypatch.setattr(es, "SVG_ELEMENTS", {"path", "rect", "g", "circle"})
    monkeypatch.setattr(es, "SEMANTIC_ELEMENTS", {"p", "section", "article", "nav"})
    yield


def test_excluded_by_parent_and_should_display(monkeypatch):
    # Ensure excluded_by_parent path uses _serialize_children
    node = make_node(tag="div", excluded_by_parent=True)

    called = {}

    def fake_serialize_children(n, include_attributes, depth):
        called['args'] = (n, include_attributes, depth)
        return "CHILDREN"

    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_children", staticmethod(fake_serialize_children))

    out = es.DOMEvalSerializer.serialize_tree(node, include_attributes=[])
    assert out == "CHILDREN"
    # confirm _serialize_children received the same node and depth 0
    assert called['args'][0] is node and called['args'][2] == 0

    # Now test should_display False uses same path
    node2 = make_node(tag="div", should_display=False)

    def fake_sc2(n, include_attributes, depth):
        return "CHILD2"

    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_children", staticmethod(fake_sc2))
    out2 = es.DOMEvalSerializer.serialize_tree(node2, include_attributes=[])
    assert out2 == "CHILD2"


def test_invisible_noncontainer_skips(monkeypatch):
    # invisible span (not container) should call _serialize_children
    node = make_node(tag="span", snapshot_node=False, is_visible=False)

    def fake_sc(n, include_attributes, depth):
        return "SKIPPED_CHILDREN"

    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_children", staticmethod(fake_sc))

    out = es.DOMEvalSerializer.serialize_tree(node, include_attributes=[], depth=1)
    assert out == "SKIPPED_CHILDREN"


def test_iframe_calls_serialize_iframe(monkeypatch):
    node = make_node(tag="iframe", snapshot_node=True, is_visible=False)

    def fake_iframe(n, include_attributes, depth):
        return "IFRAME_CONTENT"

    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_iframe", staticmethod(fake_iframe))

    out = es.DOMEvalSerializer.serialize_tree(node, include_attributes=[])
    assert out == "IFRAME_CONTENT"


def test_svg_element_and_svg_child_behavior(monkeypatch):
    # SVG top-level with interactivity and attributes
    node = make_node(tag="svg", snapshot_node=True, is_visible=True, backend_node_id=42, is_interactive=True)
    # build attributes to be attached
    monkeypatch.setattr(es.DOMEvalSerializer, "_build_compact_attributes", staticmethod(lambda orig: 'class="c"'))
    out = es.DOMEvalSerializer.serialize_tree(node, include_attributes=[])
    # Should include interactive marker and collapsed remark
    assert "[i_42]" in out
    assert "<svg" in out and 'class="c"' in out and "SVG content collapsed" in out

    # SVG child element (e.g., path) should be skipped entirely => empty string
    path_node = make_node(tag="path")
    out2 = es.DOMEvalSerializer.serialize_tree(path_node, include_attributes=[])
    assert out2 == ""


def test_element_with_attributes_scroll_inline_and_children(monkeypatch):
    # Non-container with inline text -> inline text used and no children printed
    p_node = make_node(
        tag="p",
        snapshot_node=True,
        is_visible=True,
        backend_node_id=7,
        should_show_scroll_info=True,
        scroll_text="top",
        is_interactive=True,
        children=[make_node(tag="span")],
    )

    monkeypatch.setattr(es.DOMEvalSerializer, "_build_compact_attributes", staticmethod(lambda orig: 'id="x"'))
    monkeypatch.setattr(es.DOMEvalSerializer, "_get_inline_text", staticmethod(lambda node: "hello"))
    out_p = es.DOMEvalSerializer.serialize_tree(p_node, include_attributes=[])
    # it should include interactive id marker, attributes, scroll info, and inline text, but not children
    assert "[i_7]" in out_p
    assert '<p' in out_p and 'id="x"' in out_p and 'scroll="top"' in out_p
    assert ">hello" in out_p

    # Container (div) with inline text: should still show children
    div_child = make_node(tag="li")
    div_node = make_node(
        tag="div",
        snapshot_node=True,
        is_visible=True,
        backend_node_id=9,
        is_interactive=False,
        children=[div_child],
    )
    # build compact attrs empty and inline text non-empty
    monkeypatch.setattr(es.DOMEvalSerializer, "_build_compact_attributes", staticmethod(lambda orig: ""))
    monkeypatch.setattr(es.DOMEvalSerializer, "_get_inline_text", staticmethod(lambda node: "inlineDiv"))
    # when children exist, _serialize_children should be called to append them
    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_children", staticmethod(lambda n, a, d: "CHILD_TEXT"))
    out_div = es.DOMEvalSerializer.serialize_tree(div_node, include_attributes=[])
    # Should produce a self-closing div representation line and then CHILD_TEXT on next line
    assert "<div" in out_div
    assert "inlineDiv" not in out_div  # for containers inline text shouldn't replace children (it uses ' />' form)
    assert "CHILD_TEXT" in out_div


def test_text_node_and_document_fragment(monkeypatch):
    # TEXT_NODE should result in empty string (pass branch)
    text_node = make_node(tag="#text", node_type=FakeNodeType.TEXT_NODE)
    out_text = es.DOMEvalSerializer.serialize_tree(text_node, include_attributes=[])
    assert out_text == ""

    # DOCUMENT_FRAGMENT_NODE with children should prepend #shadow and include children text
    frag_child = make_node(tag="span")
    frag_node = make_node(tag="#fragment", node_type=FakeNodeType.DOCUMENT_FRAGMENT_NODE, children=[frag_child])
    monkeypatch.setattr(es.DOMEvalSerializer, "_serialize_children", staticmethod(lambda n, a, d: "FRAG_CHILD"))
    out_frag = es.DOMEvalSerializer.serialize_tree(frag_node, include_attributes=[])
    # Expect "#shadow" line followed by children text
    assert out_frag.startswith("#shadow")
    assert "FRAG_CHILD" in out_frag


def test_serialize_tree_none_and_recursive_children(monkeypatch):
    # None input should return empty string
    assert es.DOMEvalSerializer.serialize_tree(None, include_attributes=[]) == ""

    # Test recursive child serialization via actual _serialize_children calls:
    # create many li children to trigger truncation in list containers
    children = [make_node(tag="li") for _ in range(55)]
    ul_orig = FakeOriginalNode(tag_name="ul", node_type=FakeNodeType.ELEMENT_NODE)
    ul = FakeSimplifiedNode(original_node=ul_orig, children=children)
    # Use the real _serialize_children implementation to process truncation
    out = es.DOMEvalSerializer._serialize_children(ul, include_attributes=[], depth=1)
    # Expect truncation message about more items in this list
    assert "more items in this list (truncated)" in out
