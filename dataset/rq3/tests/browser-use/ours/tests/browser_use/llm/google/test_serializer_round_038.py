import base64
import types
import pytest

from browser_use.llm.google import serializer

# Create fake domain types to patch into the serializer module.
class FakeBaseMessage:
    def model_copy(self, deep=True):
        # Return itself to simplify behavior; the serializer only needs an object copy
        return self

class FakeSystemMessage(FakeBaseMessage):
    def __init__(self, content, role=None):
        self.content = content
        self.role = role

class FakeUserMessage(FakeBaseMessage):
    def __init__(self, content, role=None):
        self.content = content
        self.role = role

class FakeAssistantMessage(FakeBaseMessage):
    def __init__(self, content, role=None):
        self.content = content
        self.role = role

# Input part-like objects used to emulate provider parts
class InPart:
    def __init__(self, type, text=None, refusal=None, image_url=None):
        self.type = type
        self.text = text
        self.refusal = refusal
        self.image_url = image_url

class ImageURL:
    def __init__(self, url, media_type):
        self.url = url
        self.media_type = media_type

# Fake Part and Content implementations used by serializer
class PartFake:
    @staticmethod
    def from_text(text: str):
        # Return a structure that preserves the text for assertions
        return {"_kind": "text", "text": text}

    @staticmethod
    def from_bytes(data: bytes, mime_type: str):
        return {"_kind": "bytes", "data": data, "mime_type": mime_type}

class ContentFake:
    def __init__(self, role, parts):
        self.role = role
        self.parts = parts

    def __repr__(self):
        return f"ContentFake(role={self.role!r}, parts={self.parts!r})"


def _patch_serializer_types():
    """
    Patch the serializer module symbols where they are resolved.
    This avoids importing real google.genai types or project message classes.
    """
    serializer.SystemMessage = FakeSystemMessage
    serializer.UserMessage = FakeUserMessage
    serializer.AssistantMessage = FakeAssistantMessage
    # Ensure BaseMessage symbol exists even if only for typing compatibility
    serializer.BaseMessage = FakeBaseMessage
    serializer.Part = PartFake
    serializer.Content = ContentFake


def test_system_message_separate_round_038():
    """
    System messages with plain string content and include_system_in_user=False
    should be extracted as the system_message and not included in formatted_messages.
    """
    _patch_serializer_types()

    sys_text = "System instruction"
    msg = FakeSystemMessage(content=sys_text)

    formatted, system = serializer.GoogleMessageSerializer.serialize_messages([msg], include_system_in_user=False)

    assert formatted == [], "No conversation messages should be returned for system-only input"
    assert system == sys_text


def test_system_iterable_parts_and_inclusion_round_038():
    """
    System messages provided as an iterable of parts should be combined with newlines.
    When include_system_in_user=True and followed by a user message the system text
    should be prepended to the first user message separated by two newlines.
    """
    _patch_serializer_types()

    # System message as iterable parts
    sys_parts = [InPart(type="text", text="line1"), InPart(type="text", text="line2")]
    system_msg = FakeSystemMessage(content=sys_parts)

    # First user message as a simple string
    user_msg = FakeUserMessage(content="Hello user")

    formatted, system = serializer.GoogleMessageSerializer.serialize_messages([system_msg, user_msg], include_system_in_user=True)

    # When include_system_in_user=True the system should be incorporated into the user content
    assert system is None
    assert len(formatted) == 1
    first = formatted[0]
    assert isinstance(first, ContentFake)
    # The first part should be a text part created by Part.from_text with system + two newlines + user content
    expected_combined = "line1\nline2\n\nHello user"
    assert first.parts[0]["_kind"] == "text"
    assert first.parts[0]["text"] == expected_combined


def test_iterable_message_parts_refusal_and_image_round_038():
    """
    A user message with an iterable content containing text, refusal and an image_url
    should produce parts in the correct order with image bytes decoded and mime type preserved.
    """
    _patch_serializer_types()

    # Prepare base64 image data deterministically
    raw = b"PNGDATA"
    b64 = base64.b64encode(raw).decode("ascii")
    url = f"data:image/png;base64,{b64}"

    parts = [
        InPart(type="text", text="greeting"),
        InPart(type="refusal", refusal="cannot comply"),
        InPart(type="image_url", image_url=ImageURL(url=url, media_type="image/png")),
    ]

    user_msg = FakeUserMessage(content=parts)

    formatted, system = serializer.GoogleMessageSerializer.serialize_messages([user_msg], include_system_in_user=False)

    assert system is None
    assert len(formatted) == 1
    content = formatted[0]
    assert content.role == "user"

    # Validate parts produced in order: text, refusal transformed, image
    assert content.parts[0]["_kind"] == "text"
    assert content.parts[0]["text"] == "greeting"

    assert content.parts[1]["_kind"] == "text"
    assert content.parts[1]["text"] == "[Refusal] cannot comply"

    # Image part must contain the decoded bytes and the mime type from the ImageURL
    assert content.parts[2]["_kind"] == "bytes"
    assert content.parts[2]["data"] == raw
    assert content.parts[2]["mime_type"] == "image/png"
