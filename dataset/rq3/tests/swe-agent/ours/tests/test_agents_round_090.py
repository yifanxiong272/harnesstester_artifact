import types
import pytest

from sweagent.agent import agents as agents_mod
from sweagent.agent.agents import DefaultAgent


class DummyTemplateRaises:
    """Dummy Template class whose render raises KeyError to exercise the exception branch."""

    def __init__(self, template_str):
        self.template_str = template_str

    def render(self, **kwargs):
        raise KeyError("missing_key")


class DummyTemplateGood:
    """Dummy Template class whose render returns a predictable string."""

    def __init__(self, template_str):
        self.template_str = template_str

    def render(self, **kwargs):
        # include template string so that multiple templates produce distinguishable output
        return f"rendered({self.template_str})"


class CapturingLogger:
    def __init__(self):
        self.debug_calls = []
        self.info_calls = []

    def debug(self, msg, *args, **kwargs):
        # store raw message and args for assertions
        self.debug_calls.append((msg, args, kwargs))

    def info(self, msg, *args, **kwargs):
        self.info_calls.append((msg, args, kwargs))


def make_agent_stub():
    """Create a DefaultAgent instance without running __init__ and with minimal attributes used by
    _add_templated_messages_to_history.
    """
    agent = object.__new__(DefaultAgent)
    agent.name = "test-agent"
    # default append history that records appended items
    agent._appended = []

    def _append_history(item):
        agent._appended.append(item)

    agent._append_history = _append_history
    return agent


def test_missing_key_logs_and_reraises_round_090(monkeypatch):
    # Patch the Template symbol in the agents module to our raising dummy to trigger KeyError branch
    monkeypatch.setattr(agents_mod, "Template", DummyTemplateRaises)

    agent = make_agent_stub()
    # format dict contains only this key (but DummyTemplateRaises will raise regardless)
    agent._get_format_dict = lambda **kwargs: {"present_key": "value"}
    fake_logger = CapturingLogger()
    agent.logger = fake_logger

    # Calling should raise the KeyError from our DummyTemplateRaises
    with pytest.raises(KeyError, match="missing_key"):
        agent._add_templated_messages_to_history(["{{missing_key}}"])

    # Ensure the debug logger was called with the available keys
    assert fake_logger.debug_calls, "logger.debug was not called in the KeyError branch"
    # The message string and the keys tuple are recorded
    msg, args, kwargs = fake_logger.debug_calls[-1]
    assert msg == "The following keys are available: %s"
    # args[0] should be a dict_keys-like iterable from _get_format_dict
    keys_iterable = args[0]
    assert list(keys_iterable) == ["present_key"]


def test_successful_render_appends_history_and_logs_round_090(monkeypatch):
    # Patch the Template symbol to a dummy that returns a predictable string
    monkeypatch.setattr(agents_mod, "Template", DummyTemplateGood)

    agent = make_agent_stub()
    # Provide format dict used by templates
    agent._get_format_dict = lambda **kwargs: {"k": "v"}
    fake_logger = CapturingLogger()
    agent.logger = fake_logger

    # Provide two templates so the message will be joined with a newline
    templates = ["t1", "t2"]
    # Provide a single tool_call_id to exercise that code path which sets role to 'tool'
    tool_call_ids = ["call-123"]

    # Call should not raise
    agent._add_templated_messages_to_history(templates, tool_call_ids=tool_call_ids)

    # One history item must have been appended
    assert len(agent._appended) == 1
    item = agent._appended[0]
    # Role should have been switched to 'tool' and tool_call_ids set
    assert item["role"] == "tool"
    assert item["tool_call_ids"] == tool_call_ids
    # Content should be the joined rendered templates in order
    expected_message = "\n".join([f"rendered({t})" for t in templates])
    assert item["content"] == expected_message
    # Agent name preserved and message_type set
    assert item["agent"] == "test-agent"
    assert item["message_type"] == "observation"

    # Ensure logger.info was called with the MODEL INPUT and our message inside
    assert fake_logger.info_calls, "logger.info was not called on successful render"
    info_msg, info_args, info_kwargs = fake_logger.info_calls[-1]
    assert "MODEL INPUT" in info_msg
    assert expected_message in info_msg
    # extra highlighter is explicitly set to None in the call
    assert info_kwargs.get("extra", {}).get("highlighter") is None
