import pytest

from sweagent.agent import agents


class DummyConfig:
    """Stand-in config with a deterministic model_copy(deep=True) method.
    The real RetryAgent only calls model_copy(deep=True) in __init__, so this
    lightweight stub is sufficient and avoids constructing the real Pydantic
    model graph.
    """

    def model_copy(self, deep=True):
        class Copied:
            def __init__(self):
                self.marker = "I am a copy"

        return Copied()


def test_retry_agent_init_round_037(monkeypatch):
    # Replace module-level collaborators where RetryAgent.__init__ resolves them
    # to ensure deterministic behavior and to observe construction side-effects.
    calls = {}

    def fake_get_logger(name, emoji=None):
        # record arguments and return a sentinel logger object
        calls['name'] = name
        calls['emoji'] = emoji
        return "SENTINEL_LOGGER"

    class FakeInstanceStats:
        def __init__(self):
            # observable marker to assert the replacement was used
            self._fake_instance_stats = True

    class FakeCombinedAgentHook:
        def __init__(self):
            self._fake_combined = True

    # Patch the symbols on the exact module where they are looked up
    monkeypatch.setattr(agents, "get_logger", fake_get_logger)
    monkeypatch.setattr(agents, "InstanceStats", FakeInstanceStats)
    monkeypatch.setattr(agents, "CombinedAgentHook", FakeCombinedAgentHook)

    cfg = DummyConfig()

    # Construct the RetryAgent under test
    ra = agents.RetryAgent(cfg)

    # Assertions covering lines 229-244 of the source: verify that
    # - config was set to the returned copy
    # - internal lists and counters are initialized
    # - get_logger was called and its return value assigned
    # - placeholders created by patched classes are used
    # - optional attributes default to None
    assert hasattr(ra, "config") and getattr(ra.config, "marker") == "I am a copy"
    assert ra._hooks == []
    assert ra._i_attempt == 0
    assert ra.logger == "SENTINEL_LOGGER"
    # verify get_logger called with the expected service name
    assert calls.get('name') == "swea-agent"
    # emoji argument should be present and be a string (logger callsite uses an emoji)
    assert isinstance(calls.get('emoji'), str)
    assert ra._agent is None
    assert ra._attempt_data == []
    assert isinstance(ra._total_instance_attempt_stats, FakeInstanceStats)
    assert isinstance(ra._chook, FakeCombinedAgentHook)
    assert ra._traj_path is None
    assert ra._problem_statement is None
    assert ra._env is None
    assert ra._output_dir is None
    assert ra._rloop is None
