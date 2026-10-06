from browser_use.dom.serializer.html_serializer import HTMLSerializer, NodeType
from types import SimpleNamespace

def test_probe_001_preserves_visible_code_with_data_in_id():
    """Probe: visible <code> with an id containing 'data' must not be dropped by serialize()."""
    # Construct serializer
    serializer = HTMLSerializer()

    # Minimal helper to create a TEXT_NODE-like object
    def text_node(val):
        return SimpleNamespace(node_type=NodeType.TEXT_NODE, node_value=val)

    # Construct a visible <code> element whose id contains the substring 'data'
    code_node = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'id': 'user-data-1', 'style': 'display: inline'},
        children=[text_node('{"key":"value"}')],
        shadow_roots=[],
        content_document=None,
        # The serializer may inspect children or children_and_shadow_roots depending on node_type
        children_and_shadow_roots=[],
    )

    output = serializer.serialize(code_node)

    # Primary behavioral oracle: visible code must be preserved (not dropped due to 'data' in id)
    assert output, "Expected non-empty serialization for a visible <code> element"
    assert ('<code' in output) or ('{"key":"value"}' in output), (
        "Serialized output must contain the <code> tag or the text content of the child;"
        f" got: {output!r}"
    )
