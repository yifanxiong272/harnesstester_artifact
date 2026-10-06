def test_probe_001():
    """Probe: turning off public cache_enabled must suppress message-level cache_control.

    We construct a tool-role Message whose content requests caching (cache_prompt=True).
    To invoke the list serializer (and thus reach the focused _list_serializer), we set
    vision_enabled=True while keeping cache_enabled=False. The conservative public
    invariant is that no top-level 'cache_control' key is emitted when cache_enabled is False.
    """

    # Local helper to build the deterministic message
    def _build_tool_message_with_cache_prompt():
        from openhands.sdk.llm.message import Message, TextContent

        return Message(role="tool", content=[TextContent(text="Probe", cache_prompt=True)])

    message = _build_tool_message_with_cache_prompt()

    # Call the public entrypoint. Ensure we exercise the list serializer by enabling vision.
    result = message.to_chat_dict(
        cache_enabled=False,
        vision_enabled=True,
        function_calling_enabled=False,
        force_string_serializer=False,
        send_reasoning_content=False,
    )

    # Primary, conservative oracle: no top-level cache_control when cache_enabled is False
    assert "cache_control" not in result, (
        "Message.to_chat_dict emitted top-level 'cache_control' despite cache_enabled=False; "
        "this reveals cache-prompt elevation ignoring the public cache flag."
    )
