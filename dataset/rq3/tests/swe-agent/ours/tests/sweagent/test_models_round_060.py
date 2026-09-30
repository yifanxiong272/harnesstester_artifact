from types import SimpleNamespace
import sweagent.agent.models as models


def _make_self(convert_system_to_user: bool):
    """Create a minimal 'self' object with config and logger needed by
    LiteLLMModel._history_to_messages. Logger.debug calls are captured in
    a list and returned alongside the self object for assertions.
    """
    logs: list[str] = []
    config = SimpleNamespace(convert_system_to_user=convert_system_to_user)
    logger = SimpleNamespace(debug=lambda msg: logs.append(msg))
    self = SimpleNamespace(config=config, logger=logger)
    return self, logs


def test_system_role_convert_round_060():
    self, logs = _make_self(True)
    history = [{"role": "system", "content": "system-message"}]

    messages = models.LiteLLMModel._history_to_messages(self, history)

    # When convert_system_to_user is True, a system role should be converted to user
    assert messages == [{"role": "user", "content": "system-message"}]

    # _history_to_messages always emits a debug log with the cache_control count
    assert logs == ["n_cache_control: 0"]


def test_system_role_not_convert_round_060():
    self, logs = _make_self(False)
    history = [{"role": "system", "content": "system-no-convert"}]

    messages = models.LiteLLMModel._history_to_messages(self, history)

    # When convert_system_to_user is False, the role should remain system
    assert messages == [{"role": "system", "content": "system-no-convert"}]
    assert logs == ["n_cache_control: 0"]


def test_tool_role_with_tool_call_and_cache_control_round_060():
    self, logs = _make_self(False)
    # role == "tool" branch: should pick tool_call_ids[0] and include cache_control
    history = [
        {
            "role": "tool",
            "content": "tool-content",
            "tool_call_ids": ["call-123"],
            "cache_control": "no-cache",
        }
    ]

    messages = models.LiteLLMModel._history_to_messages(self, history)

    assert len(messages) == 1
    m = messages[0]
    assert m["role"] == "tool"
    assert m["content"] == "tool-content"
    assert m["tool_call_id"] == "call-123"
    # cache_control key should be preserved on the message
    assert m["cache_control"] == "no-cache"

    # Since we added one cache_control, the debug message should indicate 1
    assert logs == ["n_cache_control: 1"]


def test_tool_calls_branch_round_060():
    self, logs = _make_self(False)
    # tool_calls is present (and role is not 'tool'), so the 'tool_calls' branch should run
    tool_calls_payload = [{"name": "mytool", "args": {"k": "v"}}]
    history = [{"role": "assistant", "content": "with-tool-calls", "tool_calls": tool_calls_payload}]

    messages = models.LiteLLMModel._history_to_messages(self, history)

    assert messages == [{"role": "assistant", "content": "with-tool-calls", "tool_calls": tool_calls_payload}]
    # No cache_control in this history, so debug should indicate 0
    assert logs == ["n_cache_control: 0"]
