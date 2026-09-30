import types
import pytest

from browser_use.dom.serializer import html_serializer as mod
from browser_use.dom.serializer.html_serializer import HTMLSerializer


class LocalNode:
    def __init__(self, tag_name, node_type=None, children=None):
        self.tag_name = tag_name
        # node_type will be set to the module's NodeType.ELEMENT_NODE in tests
        self.node_type = node_type
        self.children = children or []


@pytest.fixture(autouse=True)
def patch_node_type_and_serialize(monkeypatch):
    """Patch NodeType and HTMLSerializer.serialize to deterministic fakes.

    - Replace mod.NodeType with a simple stub exposing ELEMENT_NODE.
    - Replace HTMLSerializer.serialize with a fake that returns deterministic
      string values based on node.tag_name and presence of th children.
    """
    # Create a simple NodeType stub
    NodeTypeStub = types.SimpleNamespace(ELEMENT_NODE=object())
    monkeypatch.setattr(mod, "NodeType", NodeTypeStub)

    # Fake serialize implementation
    def fake_serialize(self, node, depth):
        if node is None:
            return ""
        name = getattr(node, "tag_name", None)
        # Common element name mappings
        if name == "thead":
            return "THEAD"
        if name == "tbody":
            return "TBODY"
        if name == "colgroup":
            return "COL"
        if name == "caption":
            return "CAP"
        if name == "th":
            return "TH"
        if name == "td":
            return "TD"
        if name == "tr":
            # If any child element is a <th>, mark as header row
            for c in getattr(node, "children", []):
                if getattr(c, "node_type", None) == NodeTypeStub.ELEMENT_NODE and getattr(c, "tag_name", "") == "th":
                    return "TR_HEAD"
            return "TR"
        # Default: return empty string (simulates suppressed/empty serialization)
        return ""

    monkeypatch.setattr(HTMLSerializer, "serialize", fake_serialize)
    yield


def test_empty_children_round_020():
    # Table with no children -> empty string
    s = HTMLSerializer(extract_links=False)
    # Ensure nodes use the patched NodeType
    empty_table = LocalNode("table", node_type=mod.NodeType.ELEMENT_NODE, children=[])

    res = s._serialize_table_children(empty_table, depth=0)
    assert res == ""  # covers the early-return for empty children


def test_has_thead_serializes_children_round_020():
    # Table that already contains a thead should serialize children normally
    s = HTMLSerializer(extract_links=False)
    thead = LocalNode("thead", node_type=mod.NodeType.ELEMENT_NODE)
    tr = LocalNode("tr", node_type=mod.NodeType.ELEMENT_NODE)
    # Put both children; fake_serialize returns THEAD and TR respectively
    table = LocalNode("table", node_type=mod.NodeType.ELEMENT_NODE, children=[thead, tr])

    res = s._serialize_table_children(table, depth=1)
    # Our fake_serialize returns 'THEAD' for thead and 'TR' for tr
    assert res == "THEADTR"


def test_wrap_first_tr_in_thead_and_remaining_in_tbody_round_020():
    # First <tr> contains <th> -> should wrap first in <thead> and others in <tbody>
    s = HTMLSerializer(extract_links=False)
    # Create header row with a <th>
    th = LocalNode("th", node_type=mod.NodeType.ELEMENT_NODE)
    tr_head = LocalNode("tr", node_type=mod.NodeType.ELEMENT_NODE, children=[th])
    tr2 = LocalNode("tr", node_type=mod.NodeType.ELEMENT_NODE, children=[LocalNode("td", node_type=mod.NodeType.ELEMENT_NODE)])
    table = LocalNode("table", node_type=mod.NodeType.ELEMENT_NODE, children=[tr_head, tr2])

    res = s._serialize_table_children(table, depth=0)
    # Expect thead wrapping then tbody wrapping around remaining row
    # fake_serialize returns TR_HEAD for the first tr and TR for the second
    assert res == "<thead>TR_HEAD</thead><tbody>TR</tbody>"


def test_children_before_header_and_existing_tbody_round_020():
    # When there are children before the header row (e.g. colgroup) and an existing tbody,
    # the preceding children should be emitted, the first tr wrapped in thead,
    # and the existing tbody emitted normally (no extra <tbody> wrappers).
    s = HTMLSerializer(extract_links=False)
    col = LocalNode("colgroup", node_type=mod.NodeType.ELEMENT_NODE)
    th = LocalNode("th", node_type=mod.NodeType.ELEMENT_NODE)
    tr_head = LocalNode("tr", node_type=mod.NodeType.ELEMENT_NODE, children=[th])
    existing_tbody = LocalNode("tbody", node_type=mod.NodeType.ELEMENT_NODE)

    table = LocalNode("table", node_type=mod.NodeType.ELEMENT_NODE, children=[col, tr_head, existing_tbody])

    res = s._serialize_table_children(table, depth=0)
    # Expect COL before head, then head, then the existing TBODY serialized without extra wrappers
    assert res == "COL<thead>TR_HEAD</thead>TBODY"


def test_no_header_row_detected_round_020():
    # No <tr> with <th> should fall back to normal serialization of children
    s = HTMLSerializer(extract_links=False)
    tr = LocalNode("tr", node_type=mod.NodeType.ELEMENT_NODE, children=[LocalNode("td", node_type=mod.NodeType.ELEMENT_NODE)])
    caption = LocalNode("caption", node_type=mod.NodeType.ELEMENT_NODE)
    table = LocalNode("table", node_type=mod.NodeType.ELEMENT_NODE, children=[tr, caption])

    res = s._serialize_table_children(table, depth=2)
    # fake_serialize returns TR for tr (no TH present) and CAP for caption
    assert res == "TRCAP"
