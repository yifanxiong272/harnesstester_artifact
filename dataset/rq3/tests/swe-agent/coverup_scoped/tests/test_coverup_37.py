# file: sweagent/agent/agents.py:216-223
# asked: {"lines": [219, 220, 222, 223], "branches": [[217, 219], [219, 220], [219, 222]]}
# gained: {"lines": [219, 220, 222, 223], "branches": [[217, 219], [219, 220], [219, 222]]}

import types
from types import SimpleNamespace

import pytest

import sweagent.agent.agents as agents


def test_get_agent_from_config_retry_branch(monkeypatch):
    cfg = SimpleNamespace(type="retry", extra="data")
    sentinel = object()
    seen = {}

    def fake_from_config(config):
        # ensure the same object is passed through
        seen["cfg"] = config
        return sentinel

    # Replace the RetryAgent symbol in the module with an object that has from_config
    monkeypatch.setattr(agents, "RetryAgent", SimpleNamespace(from_config=fake_from_config))
    result = agents.get_agent_from_config(cfg)
    assert result is sentinel
    assert seen["cfg"] is cfg


def test_get_agent_from_config_unknown_type_raises():
    cfg = SimpleNamespace(type="not-a-known-type")
    with pytest.raises(ValueError) as excinfo:
        agents.get_agent_from_config(cfg)
    assert "Unknown agent type: not-a-known-type" in str(excinfo.value)
