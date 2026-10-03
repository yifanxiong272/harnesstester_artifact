import browser_use.llm.google.serializer as serializer
from browser_use.llm.google.serializer import (
    GoogleMessageSerializer,
    SystemMessage,
    UserMessage,
    Part,
)


def test_probe_serialize_system_messages_aggregation_exclusion():
    # Construct deterministic parts for the second system message as plain dicts
    # These dicts match the expected ContentPartTextParam shape so pydantic will validate them
    p1 = {"type": "text", "text": "part one"}
    p2 = {"type": "text", "text": "part two"}

    # Two system messages: one plain string, one iterable of content-part dicts
    sys1 = SystemMessage(content="first system")
    sys2 = SystemMessage(content=[p1, p2])

    # Single user message whose content must remain unchanged and not include system text
    user = UserMessage(content="the user content")

    formatted_messages, system_message = GoogleMessageSerializer.serialize_messages(
        [sys1, sys2, user], include_system_in_user=False
    )

    # Primary oracle: system_message must be the concatenation in original order with single newlines
    assert system_message == "first system\npart one\npart two"

    # Observable consequences: formatted_messages should contain only the user message
    assert len(formatted_messages) == 1

    # Extract text parts from the single returned Content object and verify no system text was included
    got_texts = [p.text for p in formatted_messages[0].parts if hasattr(p, 'text')]
    assert got_texts == ["the user content"]
