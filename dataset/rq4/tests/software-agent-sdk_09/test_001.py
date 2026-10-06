def test_probe_001_blank_text_triggers_placeholder():
    """If all text blocks are blank, visualization must show the explicit placeholder.

    This directly calls the MessageEvent.visualize property fget with a minimal
    fake instance so we only exercise the method body deterministically.
    """
    from types import SimpleNamespace
    # Import the module containing the public entrypoint; use exported helpers from it.
    from openhands.sdk.event.llm_convertible import message as message_mod

    # Use the module's exported TextContent class to produce a blank text block.
    TextContent = message_mod.TextContent
    MessageEvent = message_mod.MessageEvent

    # Construct a minimal llm_message with a single blank TextContent block.
    llm_message = SimpleNamespace(content=[TextContent(text="")], responses_reasoning_item=None)

    # Build a fake self with attributes referenced by visualize.
    fake_self = SimpleNamespace(
        llm_message=llm_message,
        activated_skills=[],
        extended_content=[],
        critic_result=None,
    )

    # Call the property implementation directly to avoid full construction.
    rendered = MessageEvent.visualize.fget(fake_self)

    # rich.text.Text exposes .plain for the unstyled text; fallback to str()
    plain = getattr(rendered, "plain", str(rendered))

    # Primary behavioral oracle: placeholder must be present for blank-only content.
    assert "[no text content]" in plain
