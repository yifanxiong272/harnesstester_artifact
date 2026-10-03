def test_probe_001_prepend_system_when_assistant_between_system_and_user():
    """
    Verify that when include_system_in_user=True and the message order is
    SystemMessage, AssistantMessage, UserMessage, the serializer still prepends
    the system instruction text to the first user message (system + '\n\n' + user).

    This exercises the branch that should attach accumulated system_parts to the
    first user message even if formatted_messages already contains non-user
    messages (the reported bug hypothesis is that the implementation checks
    'not formatted_messages' and thus skips prepending if an assistant was seen
    first).
    """

    # Local imports: use the public serializer entrypoint and the project's
    # message classes so isinstance checks inside the serializer work.
    from browser_use.llm.google.serializer import GoogleMessageSerializer
    from browser_use.llm.messages import SystemMessage, AssistantMessage, UserMessage

    # Deterministic content strings
    system_text = "SYSTEM_INSTRUCTION: follow these rules"
    assistant_text = "Assistant: interim commentary"
    user_text = "User: please perform action A"

    # Construct messages in the activating order: system, assistant, then user
    messages = [
        SystemMessage(content=system_text),
        AssistantMessage(content=assistant_text),
        UserMessage(content=user_text),
    ]

    # Call the public entrypoint with the flag that should cause prepending
    formatted_messages, returned_system = GoogleMessageSerializer.serialize_messages(
        messages, include_system_in_user=True
    )

    # Find the first formatted Content with role 'user'
    first_user_content = None
    for c in formatted_messages:
        # Content.role is the string role assigned by the serializer
        if getattr(c, "role", None) == "user":
            first_user_content = c
            break

    assert first_user_content is not None, "No user Content found in formatted_messages"

    # Extract the text of the first part (the serializer uses Part.from_text for text parts)
    parts = getattr(first_user_content, "parts", None)
    assert parts and len(parts) >= 1, "User Content has no parts"

    first_part = parts[0]
    # Part.from_text sets a .text attribute for text parts
    first_part_text = getattr(first_part, "text", None)
    assert isinstance(first_part_text, str), "First part text is not a string"

    # Expected behavior: system_text, two newlines, then original user_text
    expected_text = f"{system_text}\n\n{user_text}"

    # Primary oracle: exact equality (conservative public assertion derived from docstring)
    assert first_part_text == expected_text, (
        "System text was not prepended to the first user message as expected. "
        f"Got: {first_part_text!r}, expected: {expected_text!r}"
    )
