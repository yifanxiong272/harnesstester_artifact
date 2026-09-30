import pytest
from types import SimpleNamespace

# Import the class so we execute the real method under test
from sweagent.agent.models import LiteLLMModel


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg: str) -> None:
        # store debug calls for later assertions
        self.messages.append(str(msg))


class DummySelf:
    def __init__(self, convert_system_to_user: bool):
        # minimal surface area expected by _history_to_messages
        self.config = SimpleNamespace(convert_system_to_user=convert_system_to_user)
        self.logger = DummyLogger()


def test_system_role_convert_true_round_062():
    """System role should be converted to 'user' when config.convert_system_to_user is True."""
    s = DummySelf(convert_system_to_user=True)
    history = [{"role": "system", "content": "system-message"}]

    messages = LiteLLMModel._history_to_messages(s, history)

    assert isinstance(messages, list)
    assert len(messages) == 1
    msg = messages[0]
    # get_role should return 'user' when convert_system_to_user is True -> covers the conversion branch
    assert msg["role"] == "user"
    assert msg["content"] == "system-message"


def test_role_tool_round_062():
    """Items with role 'tool' should produce a message with tool_call_id extracted from tool_call_ids and preserve cache_control if present."""
    s = DummySelf(convert_system_to_user=False)
    history = [
        {
            "role": "tool",
            "content": "tool-output",
            "tool_call_ids": ["call-123"],
            "cache_control": "no-store",
        }
    ]

    messages = LiteLLMModel._history_to_messages(s, history)

    assert len(messages) == 1
    msg = messages[0]
    # tool branch should add tool_call_id key with first id
    assert msg["role"] == "tool"
    assert msg["content"] == "tool-output"
    assert msg["tool_call_id"] == "call-123"
    # cache_control key should be preserved and added to the message
    assert msg["cache_control"] == "no-store"
    # logger.debug should have been called with an n_cache_control message
    assert any(m.startswith("n_cache_control:") for m in s.logger.messages)


def test_tool_calls_key_round_062():
    """When 'tool_calls' key exists (non-None), the corresponding message should include it under 'tool_calls'."""
    s = DummySelf(convert_system_to_user=False)
    history = [
        {"role": "assistant", "content": "assistant-content", "tool_calls": [{"id": "t1"}]}
    ]

    messages = LiteLLMModel._history_to_messages(s, history)

    assert len(messages) == 1
    msg = messages[0]
    # the elif branch should produce a message with tool_calls preserved
    assert msg["role"] == "assistant"
    assert msg["content"] == "assistant-content"
    assert "tool_calls" in msg
    assert msg["tool_calls"] == [{"id": "t1"}]


def test_cache_control_count_debug_round_062():
    """Multiple messages with cache_control should be counted and the count emitted via logger.debug."""
    s = DummySelf(convert_system_to_user=False)
    history = [
        {"role": "assistant", "content": "a1", "cache_control": "c1"},
        {"role": "assistant", "content": "a2", "cache_control": "c2"},
    ]

    messages = LiteLLMModel._history_to_messages(s, history)

    # both messages should preserve cache_control
    assert messages[0]["cache_control"] == "c1"
    assert messages[1]["cache_control"] == "c2"

    # The logger should have been called with a debug line that includes the number of cache_control occurrences.
    # The code records n_cache_control as the count of substring 'cache_control' in str(messages), so expect at least '2' here.
    found = [m for m in s.logger.messages if m.startswith("n_cache_control:")]
    assert found, "expected a debug call that starts with 'n_cache_control:'"
    # ensure the reported count is numeric and at least '2'
    reported = found[-1]
    # 'reported' is like 'n_cache_control: 2' - assert that there's a digit 2 present
    assert "2" in reported
