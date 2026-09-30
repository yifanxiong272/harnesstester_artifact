# file: sweagent/agent/agents.py:634-671
# asked: {"lines": [652, 653, 654], "branches": []}
# gained: {"lines": [652, 653, 654], "branches": []}

import logging
import pytest

import sweagent.agent.agents as agents_mod
from sweagent.agent.agents import DefaultAgent


class SimpleAgent(DefaultAgent):
    """Minimal DefaultAgent subclass that provides only what's needed for the tested method."""

    def __init__(self, base_format_dict: dict):
        # Avoid calling super().__init__ to keep initialization minimal.
        self.name = "simple-agent"
        self._base_format_dict = dict(base_format_dict)
        self._history = []
        # give each test its own logger name for clean caplog capturing
        self.logger = logging.getLogger(f"test-logger-{id(self)}")

    def _get_format_dict(self, **kwargs):
        d = dict(self._base_format_dict)
        d.update(kwargs)
        return d

    def _append_history(self, history_item: dict):
        # replicate the side-effect that the real method would have (append to history)
        self._history.append(history_item)


def test_add_templated_messages_normal_and_with_tool_call():
    agent = SimpleAgent({"x": "VALUE"})

    # Normal path: user role, observation
    agent._add_templated_messages_to_history(["Hello {{ x }}"])
    assert len(agent._history) == 1
    item = agent._history[-1]
    assert item["content"] == "Hello VALUE"
    assert item["role"] == "user"
    assert item["agent"] == agent.name
    assert item["message_type"] == "observation"

    # Tool call path: role should become 'tool' and tool_call_ids should be set
    agent2 = SimpleAgent({"y": "WORLD"})
    agent2._add_templated_messages_to_history(["{{ y }}"], tool_call_ids=["tool-123"])
    assert len(agent2._history) == 1
    item2 = agent2._history[-1]
    assert item2["content"] == "WORLD"
    assert item2["role"] == "tool"
    assert item2["tool_call_ids"] == ["tool-123"]


def test_add_templated_messages_keyerror_logs_and_re_raises(monkeypatch, caplog):
    # Create an agent with a simple format dict
    agent = SimpleAgent({"a": "1"})

    # Patch the Template used in the module so that rendering raises KeyError,
    # which should trigger the except KeyError branch in the method under test.
    class FakeTemplate:
        def __init__(self, tpl):
            self.tpl = tpl

        def render(self, **kwargs):
            raise KeyError("forced-missing-key")

    monkeypatch.setattr(agents_mod, "Template", FakeTemplate)

    # Ensure caplog captures debug messages from this agent's logger.
    caplog.set_level(logging.DEBUG, logger=agent.logger.name)

    # Using any template is fine; FakeTemplate.render will raise KeyError.
    with pytest.raises(KeyError):
        agent._add_templated_messages_to_history(["{{ anything }}"])

    # No history should have been appended on failure
    assert agent._history == []

    # Confirm that the debug message about available keys was logged and includes the mapping key name
    found_debug = False
    for rec in caplog.records:
        if rec.levelno == logging.DEBUG and "The following keys are available" in rec.getMessage():
            found_debug = True
            assert "a" in rec.getMessage()
    assert found_debug
