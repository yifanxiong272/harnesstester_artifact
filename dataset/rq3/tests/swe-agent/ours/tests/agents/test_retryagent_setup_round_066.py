import types
from pathlib import Path
import pytest

import sweagent.agent.agents as agents
from sweagent.agent.agents import RetryAgent


def test_retryagent_setup_assigns_attributes_round_066(tmp_path, monkeypatch):
    # Arrange: create an uninitialized RetryAgent instance and a minimal config
    agent = object.__new__(RetryAgent)
    agent.config = types.SimpleNamespace(retry_loop={"policy": "x"})

    # Prepare a dummy problem_statement with an id attribute and a dummy env
    problem_statement = types.SimpleNamespace(id="instance-42")
    env = types.SimpleNamespace()  # only stored on the agent
    output_dir = tmp_path / "outdir"

    # Prepare a stub for get_retry_loop_from_config to capture the call and return a sentinel
    captured = {}
    sentinel_rloop = object()

    def stub_get_retry_loop_from_config(retry_loop, problem_statement=None):
        captured['retry_loop'] = retry_loop
        captured['problem_statement'] = problem_statement
        return sentinel_rloop

    monkeypatch.setattr(
        "sweagent.agent.agents.get_retry_loop_from_config",
        stub_get_retry_loop_from_config,
    )

    # Act
    agents.RetryAgent.setup(agent, env=env, problem_statement=problem_statement, output_dir=output_dir)

    # Assert: attributes set as expected
    assert isinstance(agent._total_instance_attempt_stats, agents.InstanceStats)
    assert agent._problem_statement is problem_statement
    assert agent._traj_path == output_dir / (problem_statement.id + ".traj")
    assert agent._env is env
    assert agent._output_dir == output_dir
    # _rloop should be the sentinel returned by our stub
    assert agent._rloop is sentinel_rloop

    # And get_retry_loop_from_config was called with the config.retry_loop and the problem statement
    assert captured['retry_loop'] == agent.config.retry_loop
    assert captured['problem_statement'] is problem_statement


def test_retryagent_setup_with_empty_id_round_066(tmp_path, monkeypatch):
    # Arrange: create agent without running __init__ and with a simple config
    agent = object.__new__(RetryAgent)
    agent.config = types.SimpleNamespace(retry_loop=None)

    # problem_statement.id is an empty string -> trajectory filename should be ".traj"
    problem_statement = types.SimpleNamespace(id="")
    env = types.SimpleNamespace()
    output_dir = tmp_path

    # Stub the retry loop factory to ensure deterministic behavior
    def stub_get_retry_loop_from_config(retry_loop, problem_statement=None):
        return {"created_for": getattr(problem_statement, "id", None)}

    monkeypatch.setattr(
        "sweagent.agent.agents.get_retry_loop_from_config",
        stub_get_retry_loop_from_config,
    )

    # Act
    agents.RetryAgent.setup(agent, env=env, problem_statement=problem_statement, output_dir=output_dir)

    # Assert
    assert isinstance(agent._total_instance_attempt_stats, agents.InstanceStats)
    assert agent._traj_path == output_dir / ("" + ".traj")
    assert agent._rloop == {"created_for": ""}
