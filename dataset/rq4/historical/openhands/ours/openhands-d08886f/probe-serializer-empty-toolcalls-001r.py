from openhands.core.message import Message


def test_probe_001():
    # Use the real constructor so pydantic internals (__pydantic_fields_set__, etc.) are initialized
    msg = Message(role='user')

    # Activation conditions from the boundary plan
    msg.cache_enabled = False
    msg.vision_enabled = False
    msg.tool_call_id = None
    msg.tool_calls = []  # empty list: the boundary under test

    # Deterministic serializers that let us observe which branch was taken.
    calls = []

    def _list_serializer(self):
        calls.append("list")
        return {"which": "list"}

    def _string_serializer(self):
        calls.append("string")
        return {"which": "string"}

    # Patch the class methods so the instance will call our deterministic versions.
    orig_list = Message._list_serializer
    orig_string = Message._string_serializer
    try:
        Message._list_serializer = _list_serializer
        Message._string_serializer = _string_serializer

        # Invoke the public entrypoint under test.
        result = msg.serialize_model()
    finally:
        # Restore originals to avoid affecting other tests
        Message._list_serializer = orig_list
        Message._string_serializer = orig_string

    # Primary oracle: when tool_calls is an empty list (and no other flags),
    # the serializer selection should treat the list as absent and use the
    # string serializer. We assert both the returned value and which callable
    # was invoked to make the observation externally visible.
    assert result == {"which": "string"}, (
        "Expected string serializer result when tool_calls is empty, got: %r" % result
    )
    assert calls == ["string"], "Expected only the string serializer to be called"
