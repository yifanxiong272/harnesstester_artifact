from browser_use.llm.google import serializer


class SimpleMessage:
    """Minimal message-like object with attributes expected by serialize_messages.

    - .role: a string role (e.g., 'system', 'developer', 'user')
    - .content: either a plain string or an iterable of part-like objects (we use strings here)
    - .model_copy(deep=True): returns a copy compatible with the serializer's first step
    """
    def __init__(self, role, content):
        self.role = role
        self.content = content

    def model_copy(self, deep=True):
        # Return a shallow copy sufficient for the serializer's use
        return SimpleMessage(self.role, self.content)


def test_probe_001():
    # Prepare deterministic system/developer messages and a user message
    sys1 = "First system instruction"
    sys2 = "Second system instruction"
    user_text = "Hello from the user"

    messages = [
        SimpleMessage('system', sys1),
        SimpleMessage('developer', sys2),
        SimpleMessage('user', user_text),
    ]

    formatted_messages, system_message = (
        serializer.GoogleMessageSerializer.serialize_messages(messages, include_system_in_user=False)
    )

    # Primary oracle: system_message must be the ordered concatenation of all system/developer texts
    expected_system = "\n".join([sys1, sys2])
    assert system_message == expected_system, (
        "Expected system_message to be the newline-joined concatenation of all system/developer texts\n"
        f"expected={expected_system!r} got={system_message!r}"
    )

    # Secondary check (supporting evidence): none of the system texts should remain inside any formatted message part text
    # Extract textual content from parts conservatively
    seen_texts = []
    for content in formatted_messages:
        parts = getattr(content, 'parts', []) or []
        for part in parts:
            # Part.from_text created text parts with a .text attribute in the serializer; fall back to str(part)
            text = None
            if hasattr(part, 'text'):
                text = getattr(part, 'text')
            elif hasattr(part, 'data'):
                # binary data; skip
                text = None
            else:
                # Last resort: rely on string representation
                text = str(part)
            if text is not None:
                seen_texts.append(text)

    for sys_text in (sys1, sys2):
        for seen in seen_texts:
            assert sys_text not in seen, (
                "System/developer text was left inside formatted_messages parts, but include_system_in_user=False requires extraction:\n"
                f"system_text={sys_text!r} offending_part_text={seen!r}"
            )
