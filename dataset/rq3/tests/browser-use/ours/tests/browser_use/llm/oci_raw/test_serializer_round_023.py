import sys
import types
import importlib.util
from pathlib import Path

# Prepare a fake 'oci' package and nested modules to satisfy imports during module load
fake_oci = types.ModuleType("oci")
fake_gai = types.ModuleType("oci.generative_ai_inference")
fake_models = types.ModuleType("oci.generative_ai_inference.models")

# Minimal placeholder classes that the serializer may import (no behavior needed)
class ImageContent:
    pass

class ImageUrl:
    def __init__(self, url: str):
        self.url = url

class Message:
    pass

class TextContent:
    def __init__(self, text: str):
        self.text = text

# Attach to fake models module
fake_models.ImageContent = ImageContent
fake_models.ImageUrl = ImageUrl
fake_models.Message = Message
fake_models.TextContent = TextContent

# Wire the module hierarchy
fake_gai.models = fake_models
fake_oci.generative_ai_inference = fake_gai

# Insert into sys.modules so import statements in the serializer succeed
sys.modules["oci"] = fake_oci
sys.modules["oci.generative_ai_inference"] = fake_gai
sys.modules["oci.generative_ai_inference.models"] = fake_models

# Now load the serializer module directly from file to avoid executing package __init__
serializer_path = Path("browser_use/llm/oci_raw/serializer.py").resolve()
spec = importlib.util.spec_from_file_location("browser_use.llm.oci_raw.serializer", str(serializer_path))
serializer = importlib.util.module_from_spec(spec)
# Execute the module in isolation
spec.loader.exec_module(serializer)


# Define lightweight stubs to satisfy isinstance checks inside the serializer
class SimpleImageUrl:
    def __init__(self, url: str):
        self.url = url


class SimplePart:
    def __init__(self, type: str, text: str = None, image_url: SimpleImageUrl = None, refusal: str = None):
        self.type = type
        self.text = text
        self.image_url = image_url
        self.refusal = refusal


class UserMessageStub:
    def __init__(self, content):
        self.content = content


class SystemMessageStub:
    def __init__(self, content):
        self.content = content


class AssistantMessageStub:
    def __init__(self, content):
        self.content = content


class OtherMessageStub:
    def __str__(self):
        return "other"


def _patch_message_classes(mod):
    # Patch names on the loaded serializer module so its isinstance checks succeed
    mod.UserMessage = UserMessageStub
    mod.SystemMessage = SystemMessageStub
    mod.AssistantMessage = AssistantMessageStub


def test_serialize_messages_for_cohere_various_paths_round_023():
    # Arrange: patch serializer-local message classes
    _patch_message_classes(serializer)

    # 1) User message with string content (covers string path for User)
    user_str = UserMessageStub("Hello user")

    # 2) User message with list content including text, base64 image, and external image
    part_text = SimplePart(type="text", text="Hi")
    part_image_base64 = SimplePart(type="image_url", image_url=SimpleImageUrl("data:image/png;base64,AAAA"))
    part_image_external = SimplePart(type="image_url", image_url=SimpleImageUrl("https://example.com/img.png"))
    user_list = UserMessageStub([part_text, part_image_base64, part_image_external])

    # 3) System message with list of text parts
    sys_part = SimplePart(type="text", text="sys")
    system_list = SystemMessageStub([sys_part])

    # 4) Assistant message with text and refusal part
    assist_text = SimplePart(type="text", text="assistant text")
    assist_refusal = SimplePart(type="refusal", refusal="cannot")
    assistant_list = AssistantMessageStub([assist_text, assist_refusal])

    # 5) Other message that should hit the fallback branch (not an instance of patched classes)
    other_msg = OtherMessageStub()

    messages = [user_str, user_list, system_list, assistant_list, other_msg]

    # Act
    out = serializer.OCIRawMessageSerializer.serialize_messages_for_cohere(messages)

    # Assert: exact expected conversation pieces with placeholders and refusals
    expected_parts = [
        "User: Hello user",
        "User: Hi [Image: base64_data] [Image: external_url]",
        "System: sys",
        "Assistant: assistant text [Refusal] cannot",
        "User: other",
    ]
    expected = "\n\n".join(expected_parts)

    assert out == expected
