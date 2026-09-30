import pytest
from sweagent.agent.agents import RetryAgent, InstanceStats, CombinedAgentHook


class DummyConfig:
    """A minimal stand-in for the real RetryAgentConfig.

    The real RetryAgent.__init__ calls config.model_copy(deep=True). This dummy
    records that it was called and returns a simple value so the test can assert
    the agent stored the returned copy rather than the original object.
    """

    def __init__(self):
        self.copied = False

    def model_copy(self, deep: bool = False):
        # Record that model_copy was invoked with the deep flag and return a
        # distinct object to ensure the RetryAgent stores the returned value.
        self.copied = deep
        return {"copied_deep": deep, "original": self}


def test_retry_agent_init_round_039():
    cfg = DummyConfig()

    # Construct the agent using the dummy config. This avoids importing or
    # instantiating the real Pydantic config and keeps the test deterministic.
    agent = RetryAgent(cfg)

    # Oracle assertions verifying the __init__ behavior and all attributes set
    # on lines reported as missing in this round.
    assert cfg.copied is True, "config.model_copy was not called with deep=True"

    # The agent should store the value returned by model_copy
    assert isinstance(agent.config, dict)
    assert agent.config.get("copied_deep") is True
    assert agent.config.get("original") is cfg

    # Internal defaults initialized in __init__
    assert isinstance(agent._hooks, list) and agent._hooks == []
    assert agent._i_attempt == 0

    # logger was created; we assert it exposes the basic logging API
    assert hasattr(agent.logger, "info") and callable(agent.logger.info)

    # Agent placeholders and data structures
    assert agent._agent is None
    assert isinstance(agent._attempt_data, list) and agent._attempt_data == []

    # _total_instance_attempt_stats should be an InstanceStats instance
    assert isinstance(agent._total_instance_attempt_stats, InstanceStats)

    # Combined hook created
    assert isinstance(agent._chook, CombinedAgentHook)

    # Several optional attributes should be initialized to None
    assert agent._traj_path is None
    assert agent._problem_statement is None
    assert agent._env is None
    assert agent._output_dir is None
    assert agent._rloop is None
