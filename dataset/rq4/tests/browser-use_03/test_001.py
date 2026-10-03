def test_generated_target_probe_asset_001():
    # Exercise only the public entrypoint declared in the boundary plan
    from browser_use.dom.serializer.html_serializer import HTMLSerializer, NodeType

    # Local helper: build a minimal fake node object with the attributes the
    # serializer reads. Keep this deterministic and minimal.
    def _make_element_node(tag_name: str, attributes: dict):
        class FakeNode:
            def __init__(self):
                # Fields accessed by HTMLSerializer.serialize
                self.node_type = NodeType.ELEMENT_NODE
                self.tag_name = tag_name
                self.attributes = attributes
                # Ensure other optional attributes exist and are inert
                self.children = []
                self.shadow_roots = []
                self.content_document = None
                self.children_and_shadow_roots = []
                self.node_value = None
        return FakeNode()

    # According to stable HTML/CSS semantics, 'display: none' is case-insensitive.
    # Provide a case-variant that a case-sensitive substring check would miss.
    node = _make_element_node('code', {'style': 'Display: None'})

    serializer = HTMLSerializer()
    result = serializer.serialize(node)

    # Primary invariant assertion: the <code> element with style 'Display: None'
    # should be treated as hidden and omitted by the serializer.
    assert result == '', (
        "Expected <code> with style 'Display: None' to be omitted (empty string), "
        f"but got: {result!r}"
    )
