import types
import pytest
import sweagent.agent.agents as agents_mod

from types import SimpleNamespace


def test_get_agent_retry_round_061(monkeypatch):
    """When config.type == 'retry', get_agent_from_config should call
    RetryAgent.from_config and return its result.
    """
    calls = []

    class DummyRetry:
        @classmethod
        def from_config(cls, config):
            # record the exact object passed and return a distinct sentinel
            calls.append(config)
            return ("DUMMY_RETRY_AGENT", id(config))

    # Patch the symbol where get_agent_from_config resolves RetryAgent
    monkeypatch.setattr(agents_mod, "RetryAgent", DummyRetry)

    cfg = SimpleNamespace(type="retry")

    result = agents_mod.get_agent_from_config(cfg)

    # Assert the patched from_config was called with the same config object
    assert calls, "RetryAgent.from_config was not called"
    assert calls[0] is cfg

    # And the returned value is exactly the DummyRetry.from_config return
    assert result == ("DUMMY_RETRY_AGENT", id(cfg))


def test_get_agent_unknown_round_061():
    """When config.type is unknown, get_agent_from_config should raise a
    ValueError containing the unknown type in its message.
    """

    class Cfg:
        def __init__(self, t):
            self.type = t

    cfg = Cfg("i-am-not-a-known-agent-type")

    with pytest.raises(ValueError) as excinfo:
        agents_mod.get_agent_from_config(cfg)

    # Ensure the error message includes the exact unknown type string
    assert "Unknown agent type: i-am-not-a-known-agent-type" in str(excinfo.value)
