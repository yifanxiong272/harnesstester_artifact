# file: sweagent/agent/agents.py:227-244
# asked: {"lines": [229, 230, 231, 232, 233, 234, 235, 236, 239, 240, 241, 242, 243, 244], "branches": []}
# gained: {"lines": [229, 230, 231, 232, 233, 234, 235, 236, 239, 240, 241, 242, 243, 244], "branches": []}

import pytest

from types import SimpleNamespace

def test_retry_agent_init_sets_expected_attributes():
    # Create a dummy config object with a model_copy method that records the deep arg
    class DummyConfig:
        def __init__(self):
            self.called_with = None
            self.return_obj = {"marker": "copied_config"}
        def model_copy(self, deep=False):
            # record that model_copy was called and with what deep flag
            self.called_with = deep
            # return a new object to ensure RetryAgent stores the return value, not the original
            return {"deep": deep, "returned": self.return_obj}

    cfg = DummyConfig()

    # Import here to avoid heavy imports at module import time if pytest collects other tests
    from sweagent.agent.agents import RetryAgent

    agent = RetryAgent(cfg)

    # Verify model_copy was called with deep=True and that agent.config holds the returned object
    assert cfg.called_with is True
    assert isinstance(agent.config, dict)
    assert agent.config["deep"] is True
    assert agent.config["returned"] is cfg.return_obj

    # Verify attributes initialized in __init__ (lines 229-244)
    assert agent._hooks == []
    assert agent._i_attempt == 0
    assert agent.logger is not None
    assert agent._agent is None
    assert agent._attempt_data == []

    # Import these classes for type checks
    from sweagent.agent.models import InstanceStats
    from sweagent.agent.hooks.abstract import CombinedAgentHook

    assert isinstance(agent._total_instance_attempt_stats, InstanceStats)
    assert isinstance(agent._chook, CombinedAgentHook)

    assert agent._traj_path is None
    assert agent._problem_statement is None
    assert agent._env is None
    assert agent._output_dir is None
    assert agent._rloop is None
