# file: browser_use/dom/serializer/serializer.py:435-540
# asked: {"lines": [438, 440, 441, 442, 443, 445, 447, 449, 450, 451, 452, 453, 457, 459, 461, 462, 465, 466, 468, 470, 471, 472, 473, 474, 475, 476, 478, 479, 480, 481, 483, 484, 485, 486, 487, 488, 489, 490, 492, 493, 494, 497, 500, 501, 502, 503, 507, 508, 510, 511, 514, 515, 518, 519, 520, 521, 524, 528, 529, 532, 533, 534, 536, 537, 538, 540], "branches": [[438, 440], [438, 447], [440, 441], [440, 445], [442, 440], [442, 443], [447, 449], [447, 459], [450, 451], [450, 457], [452, 450], [452, 453], [459, 461], [459, 534], [461, 462], [461, 465], [465, 466], [465, 468], [472, 473], [472, 478], [475, 476], [475, 478], [478, 479], [478, 480], [480, 481], [480, 483], [483, 484], [483, 492], [484, 485], [484, 492], [486, 487], [486, 490], [488, 486], [488, 489], [500, 501], [500, 507], [502, 503], [502, 507], [510, 511], [510, 514], [514, 515], [514, 540], [518, 519], [518, 524], [520, 518], [520, 521], [528, 529], [528, 532], [532, 533], [532, 540], [534, 536], [534, 540], [537, 538], [537, 540]]}
# gained: {"lines": [438, 440, 441, 442, 443, 445, 447, 449, 450, 451, 452, 453, 457, 459, 461, 462, 465, 466, 468, 470, 471, 472, 473, 474, 475, 476, 478, 479, 480, 481, 483, 484, 485, 486, 487, 488, 489, 490, 492, 493, 494, 497, 500, 501, 502, 503, 507, 508, 510, 511, 514, 515, 518, 519, 520, 521, 524, 528, 529, 532, 533, 534, 536, 537, 538, 540], "branches": [[438, 440], [438, 447], [440, 441], [440, 445], [442, 440], [442, 443], [447, 449], [447, 459], [450, 451], [450, 457], [452, 453], [459, 461], [459, 534], [461, 462], [461, 465], [465, 466], [465, 468], [472, 473], [472, 478], [475, 476], [478, 479], [478, 480], [480, 481], [480, 483], [483, 484], [483, 492], [484, 485], [486, 487], [486, 490], [488, 489], [500, 501], [500, 507], [502, 503], [502, 507], [510, 511], [510, 514], [514, 515], [518, 519], [518, 524], [520, 521], [528, 529], [528, 532], [532, 533], [534, 536], [537, 538], [537, 540]]}

import pytest
from types import SimpleNamespace

from browser_use.dom.views import NodeType
from browser_use.dom.serializer import serializer as serializer_mod
from browser_use.dom.serializer.serializer import DOMTreeSerializer


class FakeNode:
    def __init__(
        self,
        node_type,
        node_name="",
        node_value="",
        attributes=None,
        is_visible=False,
        is_actually_scrollable=False,
        children_and_shadow_roots=None,
        children_nodes=None,
        content_document=None,
        tag_name=None,
        snapshot_node=None,
    ):
        self.node_type = node_type
        self.node_name = node_name
        self.node_value = node_value
        self.attributes = attributes or {}
        self.is_visible = is_visible
        # match property name used in serializer
        self.is_actually_scrollable = is_actually_scrollable
        self.children_and_shadow_roots = children_and_shadow_roots or []
        self.children_nodes = children_nodes or []
        self.content_document = content_document
        self.tag_name = tag_name
        self.snapshot_node = snapshot_node
        # some code may expect children attr; keep them in sync
        self.children = self.children_and_shadow_roots
        # minimal representation helpers
        self.node_id = 1


def make_element(**kwargs):
    return FakeNode(node_type=NodeType.ELEMENT_NODE, **kwargs)


def make_document(children=None):
    return FakeNode(node_type=NodeType.DOCUMENT_NODE, node_name="#document", children_and_shadow_roots=children or [])


def make_fragment(children=None):
    return FakeNode(node_type=NodeType.DOCUMENT_FRAGMENT_NODE, node_name="#fragment", children_and_shadow_roots=children or [])


def make_text(value, visible=True):
    return FakeNode(node_type=NodeType.TEXT_NODE, node_value=value, snapshot_node=True, is_visible=visible)


def _collect_original_nodes(simplified):
    """Traverse simplified node tree and collect original_node.node_name/node_value for assertions."""
    res = []
    if simplified is None:
        return res
    stack = [simplified]
    while stack:
        n = stack.pop()
        orig = getattr(n, "original_node", None)
        if orig is not None:
            res.append((getattr(orig, "node_name", None), getattr(orig, "node_value", None)))
        stack.extend(getattr(n, "children", []) or [])
    return res


def test_document_node_returns_first_non_none_child_and_none_when_all_excluded(monkeypatch):
    # Ensure DISABLED_ELEMENTS contains a known value for the test
    monkeypatch.setattr(serializer_mod, "DISABLED_ELEMENTS", {"noscript"}, raising=False)
    monkeypatch.setattr(serializer_mod, "SVG_ELEMENTS", set(), raising=False)

    # Create an element child that will be included (visible)
    child_elem = make_element(node_name="div", is_visible=True, children_and_shadow_roots=[])
    doc = make_document(children=[child_elem])

    s = DOMTreeSerializer(root_node=doc)
    # prevent compound-components logic side effects
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)

    simplified = s._create_simplified_tree(doc)
    assert simplified is not None
    # The returned simplified node should be the simplified for 'div' (original_node should be child_elem)
    originals = _collect_original_nodes(simplified)
    # node_value for element defaults to empty string in FakeNode
    assert (child_elem.node_name, "") in originals

    # Now test that if the only child is a disabled element, returns None
    disabled_child = make_element(node_name="noscript", is_visible=True)
    doc2 = make_document(children=[disabled_child])
    s2 = DOMTreeSerializer(root_node=doc2)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    assert s2._create_simplified_tree(doc2) is None


def test_document_fragment_returns_empty_and_with_children(monkeypatch):
    monkeypatch.setattr(serializer_mod, "DISABLED_ELEMENTS", set(), raising=False)
    monkeypatch.setattr(serializer_mod, "SVG_ELEMENTS", set(), raising=False)

    # Fragment with no meaningful children => should return an empty SimplifiedNode (not None)
    frag_empty = make_fragment(children=[])
    s = DOMTreeSerializer(root_node=frag_empty)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    result_empty = s._create_simplified_tree(frag_empty)
    assert result_empty is not None
    assert getattr(result_empty, "original_node") is frag_empty
    assert getattr(result_empty, "children") == []

    # Fragment with a meaningful child -> child should be processed and appended
    inner = make_element(node_name="div", is_visible=True)
    frag_with_child = make_fragment(children=[inner])
    s2 = DOMTreeSerializer(root_node=frag_with_child)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    result = s2._create_simplified_tree(frag_with_child)
    assert result is not None
    # The fragment simplified node should have one child whose original_node is inner
    assert len(result.children) == 1
    assert result.children[0].original_node is inner


def test_element_exclude_session_and_legacy_and_iframe_and_validation_and_file_and_shadow_and_scroll(monkeypatch):
    # Prepare sets so name checks are predictable
    monkeypatch.setattr(serializer_mod, "DISABLED_ELEMENTS", {"disabledtag"}, raising=False)
    monkeypatch.setattr(serializer_mod, "SVG_ELEMENTS", {"svgpath"}, raising=False)

    # session-specific exclude attribute
    node_sess = make_element(node_name="div", is_visible=True, attributes={})
    node_sess.attributes = {"data-browser-use-exclude-abc": "true"}
    s = DOMTreeSerializer(root_node=node_sess, session_id="abc")
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    assert s._create_simplified_tree(node_sess) is None

    # legacy exclude attribute (case-insensitive)
    node_legacy = make_element(node_name="div", is_visible=True, attributes={"data-browser-use-exclude": "TrUe"})
    s2 = DOMTreeSerializer(root_node=node_legacy)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    assert s2._create_simplified_tree(node_legacy) is None

    # IFRAME with content_document children
    iframe_child = make_element(node_name="span", is_visible=True)
    content_doc = SimpleNamespace(children_nodes=[iframe_child])
    iframe = make_element(node_name="IFRAME", is_visible=True, content_document=content_doc)
    s3 = DOMTreeSerializer(root_node=iframe)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res_iframe = s3._create_simplified_tree(iframe)
    assert res_iframe is not None
    assert len(res_iframe.children) == 1
    assert res_iframe.children[0].original_node is iframe_child

    # Validation attributes force visibility when originally not visible
    val_node = make_element(node_name="input", is_visible=False, attributes={"aria-label": "x"})
    s4 = DOMTreeSerializer(root_node=val_node)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res_val = s4._create_simplified_tree(val_node)
    assert res_val is not None
    assert res_val.original_node is val_node

    # File input forces visibility even if hidden
    file_node = make_element(node_name="input", is_visible=False, tag_name="input", attributes={"type": "file"})
    s5 = DOMTreeSerializer(root_node=file_node)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res_file = s5._create_simplified_tree(file_node)
    assert res_file is not None
    assert res_file.original_node is file_node

    # Shadow host detection: host has a document fragment child which contains a visible child
    shadow_inner = make_element(node_name="p", is_visible=True)
    shadow_fragment = make_fragment(children=[shadow_inner])
    host = make_element(node_name="div", is_visible=False, children_and_shadow_roots=[shadow_fragment])
    s6 = DOMTreeSerializer(root_node=host)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res_host = s6._create_simplified_tree(host)
    # Because it's a shadow host and has children, the simplified should be returned immediately
    assert res_host is not None
    assert res_host.original_node is host
    # It should contain the shadow fragment simplified under it, which in turn contains the inner element
    assert any(
        (child.original_node is shadow_fragment and any(grand.original_node is shadow_inner for grand in (child.children or [])))
        for child in res_host.children
    )

    # Scrollable element included even if not visible
    scroll_node = make_element(node_name="div", is_visible=False, is_actually_scrollable=True)
    s7 = DOMTreeSerializer(root_node=scroll_node)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res_scroll = s7._create_simplified_tree(scroll_node)
    assert res_scroll is not None
    assert res_scroll.original_node is scroll_node


def test_text_node_handling_and_svg_disabled(monkeypatch):
    # Ensure SVG elements gets skipped
    monkeypatch.setattr(serializer_mod, "SVG_ELEMENTS", {"path", "rect"}, raising=False)
    monkeypatch.setattr(serializer_mod, "DISABLED_ELEMENTS", set(), raising=False)

    # Text node that is visible and has meaningful content (>1 char) should be included
    text = make_text("Hello", visible=True)
    s = DOMTreeSerializer(root_node=text)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    res = s._create_simplified_tree(text)
    assert res is not None
    assert res.original_node is text

    # Text node that is invisible or too short should be excluded
    text_short = make_text("a", visible=True)  # length 1 -> excluded
    s2 = DOMTreeSerializer(root_node=text_short)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    assert s2._create_simplified_tree(text_short) is None

    # SVG element should be excluded based on SVG_ELEMENTS set
    svg_elem = make_element(node_name="path", is_visible=True)
    s3 = DOMTreeSerializer(root_node=svg_elem)
    monkeypatch.setattr(DOMTreeSerializer, "_add_compound_components", lambda self, simplified, node: None)
    assert s3._create_simplified_tree(svg_elem) is None
