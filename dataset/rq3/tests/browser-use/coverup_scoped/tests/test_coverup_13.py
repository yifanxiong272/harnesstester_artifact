# file: browser_use/llm/oci_raw/serializer.py:159-229
# asked: {"lines": [159, 160, 173, 175, 176, 178, 179, 180, 181, 183, 184, 185, 186, 187, 190, 191, 193, 194, 196, 198, 199, 200, 201, 203, 204, 205, 206, 207, 209, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221, 222, 224, 227, 229], "branches": [[175, 176], [175, 229], [178, 179], [178, 198], [179, 180], [179, 181], [181, 183], [181, 196], [184, 185], [184, 194], [185, 186], [185, 187], [187, 184], [187, 190], [190, 191], [190, 193], [198, 199], [198, 211], [199, 200], [199, 201], [201, 203], [201, 209], [204, 205], [204, 207], [205, 204], [205, 206], [211, 212], [211, 227], [212, 213], [212, 214], [214, 216], [214, 224], [217, 218], [217, 222], [218, 219], [218, 220], [220, 217], [220, 221]]}
# gained: {"lines": [159, 160, 173, 175, 176, 178, 179, 180, 181, 183, 184, 185, 186, 187, 190, 191, 193, 194, 196, 198, 199, 201, 203, 204, 205, 206, 207, 209, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221, 222, 224, 227, 229], "branches": [[175, 176], [175, 229], [178, 179], [178, 198], [179, 180], [179, 181], [181, 183], [181, 196], [184, 185], [184, 194], [185, 186], [185, 187], [187, 190], [190, 191], [190, 193], [198, 199], [198, 211], [199, 201], [201, 203], [204, 205], [204, 207], [205, 206], [211, 212], [211, 227], [212, 213], [212, 214], [214, 216], [217, 218], [217, 222], [218, 219], [218, 220], [220, 221]]}

import sys
import types
import importlib.util
from pathlib import Path
import pytest


def _load_serializer_module(monkeypatch):
    """
    Load the serializer.py module without requiring real 'oci' package or
    executing package __init__ files. Inserts fake minimal modules into
    sys.modules to satisfy imports.
    Returns the loaded module.
    """
    repo_root = Path.cwd()
    mod_path = repo_root / "browser_use" / "llm" / "oci_raw" / "serializer.py"
    if not mod_path.exists():
        raise FileNotFoundError(f"serializer.py not found at expected path: {mod_path}")

    # Create fake oci.generative_ai_inference.models module with minimal classes
    fake_oci = types.ModuleType("oci")
    fake_gaii = types.ModuleType("oci.generative_ai_inference")
    fake_models = types.ModuleType("oci.generative_ai_inference.models")

    class ImageContent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class ImageUrl:
        def __init__(self, url: str):
            self.url = url

    class TextContent:
        def __init__(self, text: str):
            self.text = text

    class Message:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_models.ImageContent = ImageContent
    fake_models.ImageUrl = ImageUrl
    fake_models.TextContent = TextContent
    fake_models.Message = Message

    # Insert into sys.modules using monkeypatch so teardown is automatic
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setitem(sys.modules, "oci.generative_ai_inference", fake_gaii)
    monkeypatch.setitem(sys.modules, "oci.generative_ai_inference.models", fake_models)

    # Provide a minimal browser_use.llm.messages module so serializer's import succeeds
    fake_messages = types.ModuleType("browser_use.llm.messages")

    class BaseMessage:
        pass

    class ContentPartImageParam:
        def __init__(self, url: str):
            self.url = url

    # Minimal placeholders for message classes (real test will monkeypatch module attrs)
    class UserMessage(BaseMessage):
        pass

    class SystemMessage(BaseMessage):
        pass

    class AssistantMessage(BaseMessage):
        pass

    fake_messages.BaseMessage = BaseMessage
    fake_messages.ContentPartImageParam = ContentPartImageParam
    fake_messages.UserMessage = UserMessage
    fake_messages.SystemMessage = SystemMessage
    fake_messages.AssistantMessage = AssistantMessage

    monkeypatch.setitem(sys.modules, "browser_use.llm.messages", fake_messages)

    # Load the serializer module by file path under its full package name to keep consistency
    name = "browser_use.llm.oci_raw.serializer"
    spec = importlib.util.spec_from_file_location(name, str(mod_path))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


# Helper test classes and parts used to simulate messages and content parts
class TestBaseMessage:
    def __str__(self):
        return f"<BaseMessage {self.__class__.__name__}>"


class TestUserMessage(TestBaseMessage):
    def __init__(self, content):
        self.content = content


class TestSystemMessage(TestBaseMessage):
    def __init__(self, content):
        self.content = content


class TestAssistantMessage(TestBaseMessage):
    def __init__(self, content):
        self.content = content


class TestOtherMessage(TestBaseMessage):
    def __init__(self):
        pass

    def __str__(self):
        return "OTHER_MESSAGE_REPR"


class TextPart:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class ImageURL:
    def __init__(self, url):
        self.url = url


class ImagePart:
    def __init__(self, url):
        self.type = "image_url"
        self.image_url = ImageURL(url)


class RefusalPart:
    def __init__(self, refusal):
        self.type = "refusal"
        self.refusal = refusal


@pytest.mark.parametrize("base64_url,external_url", [
    ("data:image/png;base64,AAAA", "https://example.com/img.png"),
    ("data:image/gif;base64,XYZ", "http://cdn.test/image.jpg"),
])
def test_serialize_messages_for_cohere_all_branches(monkeypatch, base64_url, external_url):
    # Load module with fake dependencies
    mod = _load_serializer_module(monkeypatch)
    OCIRawMessageSerializer = mod.OCIRawMessageSerializer

    # Monkeypatch the message classes inside the loaded module so isinstance checks match
    monkeypatch.setattr(mod, "BaseMessage", TestBaseMessage, raising=False)
    monkeypatch.setattr(mod, "UserMessage", TestUserMessage, raising=False)
    monkeypatch.setattr(mod, "SystemMessage", TestSystemMessage, raising=False)
    monkeypatch.setattr(mod, "AssistantMessage", TestAssistantMessage, raising=False)

    # 1. UserMessage with simple string content
    m1 = TestUserMessage("hello user")

    # 2. UserMessage with list content: text, base64 image, external image
    m2_parts = [
        TextPart("hi there"),
        ImagePart(base64_url),
        ImagePart(external_url),
    ]
    m2 = TestUserMessage(m2_parts)

    # 3. SystemMessage with list content of text parts
    m3 = TestSystemMessage([TextPart("system note")])

    # 4. AssistantMessage with string content
    m4 = TestAssistantMessage("assistant reply")

    # 5. AssistantMessage with list content including text and refusal
    m5 = TestAssistantMessage([TextPart("assistant part"), RefusalPart("cannot comply with request")])

    # 6. Other message type to trigger fallback (not User/System/Assistant)
    m6 = TestOtherMessage()

    messages = [m1, m2, m3, m4, m5, m6]

    out = OCIRawMessageSerializer.serialize_messages_for_cohere(messages)

    expected_parts = [
        "User: hello user",
        "User: hi there [Image: base64_data] [Image: external_url]",
        "System: system note",
        "Assistant: assistant reply",
        "Assistant: assistant part [Refusal] cannot comply with request",
        "User: OTHER_MESSAGE_REPR",
    ]
    expected = "\n\n".join(expected_parts)

    assert out == expected


def test_serialize_messages_for_cohere_handles_nonstandard_content_types(monkeypatch):
    mod = _load_serializer_module(monkeypatch)
    OCIRawMessageSerializer = mod.OCIRawMessageSerializer

    # Monkeypatch the message classes inside the loaded module
    monkeypatch.setattr(mod, "BaseMessage", TestBaseMessage, raising=False)
    monkeypatch.setattr(mod, "UserMessage", TestUserMessage, raising=False)
    monkeypatch.setattr(mod, "SystemMessage", TestSystemMessage, raising=False)
    monkeypatch.setattr(mod, "AssistantMessage", TestAssistantMessage, raising=False)

    # UserMessage with content that's neither str nor list (e.g., an int)
    m1 = TestUserMessage(12345)

    # SystemMessage with empty list -> should produce empty content
    m2 = TestSystemMessage([])

    # AssistantMessage with empty list -> should produce empty content
    m3 = TestAssistantMessage([])

    out = OCIRawMessageSerializer.serialize_messages_for_cohere([m1, m2, m3])

    expected_parts = [
        "User: ",   # content stays as initial empty string for non-str/list
        "System: ",  # empty list -> no text parts -> empty content
        "Assistant: ",  # empty list -> no text parts -> empty content
    ]
    expected = "\n\n".join(expected_parts)

    assert out == expected
    # Also assert that no unexpected tokens like '[Image' or '[Refusal]' are present
    assert "[Image" not in out
    assert "[Refusal]" not in out
