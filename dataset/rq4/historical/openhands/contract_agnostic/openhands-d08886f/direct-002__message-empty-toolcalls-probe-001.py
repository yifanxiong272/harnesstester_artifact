def test_probe_001():
    # Exercise the public instance method Message.serialize_model and observe which serializer branch is chosen
    from openhands.core.message import Message
    import types

    # Deterministic construction: set feature flags to False/None and tool_calls to an explicit empty list
    msg = Message.construct(
        cache_enabled=False,
        vision_enabled=False,
        tool_call_id=None,
        tool_calls=[],
    )

    # Patch the instance's serializers with small, deterministic stubs so we can observe which one is invoked
    def _fake_string(self):
        return {"content": "joined text (string)"}

    def _fake_list(self):
        return {"content": ["list_item"]}

    msg._string_serializer = types.MethodType(_fake_string, msg)
    msg._list_serializer = types.MethodType(_fake_list, msg)

    # Invoke the public entrypoint
    result = msg.serialize_model()

    # Primary oracle: content must be a string (empty tool_calls should not force list-style serialization)
    content = result.get("content")
    assert isinstance(content, str), f"Expected string content but got {type(content)}: {content}"
