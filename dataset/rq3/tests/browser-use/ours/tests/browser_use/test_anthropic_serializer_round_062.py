import importlib
import pytest

# Import the module under test
serializer_module = importlib.import_module('browser_use.llm.anthropic.serializer')
AnthropicMessageSerializer = serializer_module.AnthropicMessageSerializer

# Provide simple factories to stand in for the anthropic.types constructors used by the
# serializer. These return plain dicts so the serializer's dict-access checks work.

def _make_message_param(**kwargs):
    # Mirror the usage in serializer: MessageParam(role=..., content=...)
    return {'role': kwargs.get('role'), 'content': kwargs.get('content')}

def _make_text_block_param(**kwargs):
    # Ensure keys 'text' and 'type' and 'cache_control' exist when called
    return {
        'text': kwargs.get('text'),
        'type': kwargs.get('type'),
        'cache_control': kwargs.get('cache_control')
    }

# Patch the serializer module-level names used inside serialize so tests can control outputs.
serializer_module.MessageParam = _make_message_param
serializer_module.TextBlockParam = _make_text_block_param

# Helper simple message classes used only for isinstance checks by the serializer.
class _UMsg:
    def __init__(self, content, cache=False):
        self.content = content
        self.cache = cache

class _SMsg:
    pass

class _AMsg:
    def __init__(self, content=None, cache=False, tool_calls=None):
        self.content = content
        self.cache = cache
        self.tool_calls = tool_calls or []

# Assign these into the module where isinstance checks look them up.
serializer_module.UserMessage = _UMsg
serializer_module.SystemMessage = _SMsg
serializer_module.AssistantMessage = _AMsg

# We'll also stub out two internal helpers to produce deterministic block shapes
# when the serializer calls them for parts or tool calls.
def _stub_serialize_content_part_text(part, use_cache=False):
    # Expect part to have a 'text' attribute for our tests
    return {'text': getattr(part, 'text', ''), 'type': 'text', 'cache_control': None}

def _stub_serialize_tool_calls_to_content(tool_calls, use_cache=False):
    # Return a deterministic tool block representation
    return [{'type': 'tool', 'tool_calls_len': len(tool_calls)}]

# Patch these helpers on the serializer class
AnthropicMessageSerializer._serialize_content_part_text = staticmethod(_stub_serialize_content_part_text)
AnthropicMessageSerializer._serialize_tool_calls_to_content = staticmethod(_stub_serialize_tool_calls_to_content)

# Tests

def test_user_message_round_062():
    """UserMessage path should call _serialize_content and wrap in MessageParam."""
    # Patch internal _serialize_content to a deterministic stub for this test
    original = AnthropicMessageSerializer._serialize_content

    try:
        AnthropicMessageSerializer._serialize_content = staticmethod(lambda content, use_cache: f"SER:{content}")
        msg = _UMsg(content='hello-user', cache=True)
        out = AnthropicMessageSerializer.serialize(msg)
        assert isinstance(out, dict)
        assert out['role'] == 'user'
        assert out['content'] == 'SER:hello-user'
    finally:
        AnthropicMessageSerializer._serialize_content = original


def test_system_message_round_062():
    """SystemMessage should be returned unchanged (converted earlier in pipeline).
    This verifies the SystemMessage branch returns the passed object.
    """
    sys_msg = _SMsg()
    out = AnthropicMessageSerializer.serialize(sys_msg)
    # The serializer returns the message object itself for SystemMessage
    assert out is sys_msg


def test_assistant_string_content_simplify_round_062():
    """AssistantMessage with string content, no cache and no tool calls should be simplified
    to a plain string (not a block list).
    """
    msg = _AMsg(content='assistant text', cache=False, tool_calls=[])

    out = AnthropicMessageSerializer.serialize(msg)
    assert isinstance(out, dict)
    assert out['role'] == 'assistant'
    # When single text block and no cache, content should be simplified to the raw string
    assert out['content'] == 'assistant text'


def test_assistant_content_list_part_round_062():
    """AssistantMessage where content is a list of parts should go through the
    content-part serialization branch and simplify when appropriate.
    """
    # Build a simple part-like object with a text attribute
    class Part:
        def __init__(self, text):
            self.type = 'text'
            self.text = text

    part = Part('part text')
    msg = _AMsg(content=[part], cache=False, tool_calls=[])

    out = AnthropicMessageSerializer.serialize(msg)
    assert out['role'] == 'assistant'
    # Simplified to the part.text string
    assert out['content'] == 'part text'


def test_assistant_tool_calls_yield_list_round_062():
    """AssistantMessage with no textual content but with tool_calls should produce a
    list content (tool blocks), not be simplified to a string.
    """
    msg = _AMsg(content=None, cache=False, tool_calls=[{'call': 'x'}])
    out = AnthropicMessageSerializer.serialize(msg)
    assert out['role'] == 'assistant'
    # Content should be the list of tool blocks we stubbed
    assert isinstance(out['content'], list)
    assert out['content'] == [{'type': 'tool', 'tool_calls_len': 1}]


def test_unknown_message_type_raises_round_062():
    """Passing an object that is not a recognized message type should raise ValueError."""
    class NotAMessage:
        pass

    not_msg = NotAMessage()
    with pytest.raises(ValueError) as exc:
        AnthropicMessageSerializer.serialize(not_msg)
    assert 'Unknown message type' in str(exc.value)
