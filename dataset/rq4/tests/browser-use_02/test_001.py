def test_probe_001_preserve_visible_code_with_id_containing_data():
    """Ensure visible <code> elements with ids containing 'data' are not omitted by the serializer.

    This test constructs minimal node-like objects (SimpleNamespace) matching the attributes the
    HTMLSerializer.serialize implementation accesses and calls the public entrypoint. The oracle
    asserts a single combined condition so the test stands/falls on one primary behavioral check.
    """
    from types import SimpleNamespace
    from browser_use.dom.serializer.html_serializer import HTMLSerializer, NodeType

    # Text child that should be serialized (contains characters to ensure content is visible)
    text_node = SimpleNamespace(node_type=NodeType.TEXT_NODE, node_value='visible content')

    # ELEMENT_NODE 'code' with an id that includes the substring 'data' but no hiding style
    code_node = SimpleNamespace(
        node_type=NodeType.ELEMENT_NODE,
        tag_name='code',
        attributes={'id': 'user-data'},
        children=[text_node],
        shadow_roots=[],
        shadow_root_type=None,
        content_document=None,
    )

    serialized = HTMLSerializer().serialize(code_node)

    # Single primary assertion: non-empty and contains opening+closing tags, the text, and the id
    ok = bool(serialized) and '<code' in serialized and '</code>' in serialized and 'visible content' in serialized and 'user-data' in serialized
    assert ok, f"Serializer unexpectedly omitted or altered visible <code> element: {serialized!r}"
