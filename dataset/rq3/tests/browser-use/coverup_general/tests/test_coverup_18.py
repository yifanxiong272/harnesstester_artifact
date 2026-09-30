# file: browser_use/dom/service.py:70-182
# asked: {"lines": [77, 79, 80, 82, 83, 84, 85, 87, 88, 89, 90, 91, 93, 95, 97, 99, 100, 102, 104, 105, 106, 107, 108, 109, 110, 111, 112, 115, 116, 117, 118, 120, 121, 122, 123, 124, 128, 129, 131, 132, 134, 136, 138, 139, 141, 142, 143, 145, 146, 147, 149, 151, 154, 155, 156, 157, 160, 161, 162, 164, 166, 167, 170, 171, 173, 174, 176, 177, 179, 180, 182], "branches": [[79, 80], [79, 82], [99, 100], [99, 128], [102, 104], [102, 128], [105, 106], [105, 107], [107, 108], [107, 115], [116, 117], [116, 118], [128, 129], [128, 131], [131, 132], [131, 134], [138, 139], [138, 141], [141, 142], [141, 145], [142, 141], [142, 143], [145, 146], [145, 149], [146, 145], [146, 147], [153, 160], [153, 173], [161, 162], [161, 164], [170, 171], [170, 173], [173, 174], [173, 176], [176, 177], [176, 179], [179, 0], [179, 180]]}
# gained: {"lines": [77, 79, 80, 82, 83, 84, 85, 87, 88, 89, 90, 91, 93, 95, 97, 99, 100, 102, 104, 105, 107, 115, 116, 117, 118, 120, 121, 122, 123, 124, 128, 129, 131, 132, 134, 136, 138, 139, 141, 142, 143, 151, 154, 155, 156, 157, 160, 161, 162, 164, 166, 167, 170, 171, 173, 174, 176, 177, 179, 180, 182], "branches": [[79, 80], [79, 82], [99, 100], [99, 128], [102, 104], [102, 128], [105, 107], [107, 115], [116, 117], [128, 129], [128, 131], [131, 132], [131, 134], [138, 139], [138, 141], [141, 142], [142, 143], [153, 160], [153, 173], [161, 162], [170, 171], [170, 173], [173, 174], [173, 176], [176, 177], [176, 179], [179, 0], [179, 180]]}

import logging
from types import SimpleNamespace

import pytest

from browser_use.dom.service import DomService
from browser_use.dom.serializer.clickable_elements import ClickableElementDetector
from browser_use.dom.views import NodeType


class MockBounds:
    def __init__(self, y):
        self.y = y


class MockClientRects:
    def __init__(self, height):
        self.height = height


class MockSnapshotNode:
    def __init__(self, bounds=None, clientRects=None, computed_styles=None):
        self.bounds = bounds
        self.clientRects = clientRects
        self.computed_styles = computed_styles or {}


class MockAXNode:
    def __init__(self, name=None):
        self.name = name


class MockNode:
    def __init__(
        self,
        node_type=NodeType.ELEMENT_NODE,
        tag_name=None,
        is_visible=None,
        snapshot_node=None,
        ax_node=None,
        attributes=None,
        children_nodes=None,
        shadow_roots=None,
        content_document=None,
    ):
        self.node_type = node_type
        self.tag_name = tag_name
        self.is_visible = is_visible
        self.snapshot_node = snapshot_node
        self.ax_node = ax_node
        self.attributes = attributes or {}
        self.children_nodes = children_nodes or []
        self.shadow_roots = shadow_roots or []
        self.content_document = content_document
        # fields set/used by DomService
        self.hidden_elements_info = []
        self.has_hidden_content = False
        # optional marker used by our monkeypatched is_interactive
        self.make_interactive = False


def make_service():
    browser_session = SimpleNamespace(logger=logging.getLogger("test"))
    return DomService(browser_session=browser_session)


def test_count_hidden_elements_collects_hidden_interactive_and_respects_css_and_visibility(monkeypatch):
    svc = make_service()

    # Monkeypatch ClickableElementDetector to treat nodes with .make_interactive True as interactive
    monkeypatch.setattr(
        ClickableElementDetector,
        "is_interactive",
        staticmethod(lambda node: getattr(node, "make_interactive", False)),
    )

    # Create an interactive child that is hidden by threshold (opacity invalid -> ValueError path)
    child1_snapshot = MockSnapshotNode(bounds=MockBounds(y=250.0), computed_styles={"opacity": "abc"})
    child1 = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="button",
        is_visible=False,
        snapshot_node=child1_snapshot,
        ax_node=None,
        attributes={},
    )
    child1.make_interactive = True

    # Create an interactive child that is CSS-hidden via opacity '0' (should NOT be collected)
    child2_snapshot = MockSnapshotNode(bounds=MockBounds(y=300.0), computed_styles={"opacity": "0"})
    child2 = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="input",
        is_visible=False,
        snapshot_node=child2_snapshot,
        ax_node=None,
        attributes={},
    )
    child2.make_interactive = True

    # Create an interactive child that is visible (should NOT be collected)
    child3_snapshot = MockSnapshotNode(bounds=MockBounds(y=400.0), computed_styles={})
    child3 = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="a",
        is_visible=True,
        snapshot_node=child3_snapshot,
        ax_node=None,
        attributes={},
    )
    child3.make_interactive = True

    # Put child1, child2, child3 under content_document to be found by collect_hidden_elements
    content_doc = MockNode(node_type=NodeType.DOCUMENT_NODE, tag_name="#document", children_nodes=[child1, child2, child3])

    # Iframe node with client rects height = 100 so pages calculation = y / 100
    iframe_snapshot = MockSnapshotNode(clientRects=MockClientRects(height=100.0))
    iframe = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="IFRAME",
        is_visible=True,
        snapshot_node=iframe_snapshot,
        content_document=content_doc,
    )

    # Execute the method
    svc._count_hidden_elements_in_iframes(iframe)

    # Only child1 should be collected: child2 is CSS-hidden, child3 is visible
    assert isinstance(iframe.hidden_elements_info, list)
    assert len(iframe.hidden_elements_info) == 1
    info = iframe.hidden_elements_info[0]
    assert info["tag"] == "button"
    # child1 had no ax name and no attributes -> should use '(no label)'
    assert info["text"] == "(no label)"
    # pages = round(250 / 100, 1) -> 2.5
    assert info["pages"] == 2.5


def test_count_hidden_elements_sets_has_hidden_content_when_no_interactive_but_hidden_noninteractive(monkeypatch):
    svc = make_service()

    # Monkeypatch ClickableElementDetector to always return False (no interactive elements)
    monkeypatch.setattr(ClickableElementDetector, "is_interactive", staticmethod(lambda node: False))

    # Create a non-interactive node that is hidden by threshold (opacity invalid -> ValueError path)
    hidden_snapshot = MockSnapshotNode(bounds=MockBounds(y=120.0), computed_styles={"opacity": "not_a_number"})
    hidden_node = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="div",
        is_visible=False,
        snapshot_node=hidden_snapshot,
        ax_node=None,
        attributes={},
    )

    # Create a shadow root under content_document to ensure shadow_roots recursion is covered
    shadow_hidden_snapshot = MockSnapshotNode(bounds=MockBounds(y=220.0), computed_styles={"opacity": "not_a_number"})
    shadow_hidden = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="span",
        is_visible=False,
        snapshot_node=shadow_hidden_snapshot,
        ax_node=None,
        attributes={},
    )

    content_doc = MockNode(
        node_type=NodeType.DOCUMENT_NODE,
        tag_name="#document",
        children_nodes=[hidden_node],
        shadow_roots=[shadow_hidden],
    )

    # Iframe node with client rects height = 200
    iframe_snapshot = MockSnapshotNode(clientRects=MockClientRects(height=200.0))
    iframe = MockNode(
        node_type=NodeType.ELEMENT_NODE,
        tag_name="iframe",
        is_visible=True,
        snapshot_node=iframe_snapshot,
        content_document=content_doc,
    )

    # Execute the method
    svc._count_hidden_elements_in_iframes(iframe)

    # No interactive elements were found, but there is hidden non-interactive content -> has_hidden_content True
    assert iframe.hidden_elements_info == []
    assert iframe.has_hidden_content is True
