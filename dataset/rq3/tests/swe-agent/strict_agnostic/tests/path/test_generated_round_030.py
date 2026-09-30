import builtins
from pathlib import Path
import types
import pytest

import sweagent.agent.agents as agents


class _StubAgent:
    def __init__(self):
        self.added_hooks = []
        self.setup_called_with = None

    def add_hook(self, hook):
        # record hook additions
        self.added_hooks.append(hook)

    def setup(self, env, problem_statement, output_dir):
        # record the exact args to assert later
        self.setup_called_with = {
            "env": env,
            "problem_statement": problem_statement,
            "output_dir": output_dir,
        }


class DummyModel:
    def __init__(self, per_instance_cost_limit):
        self.per_instance_cost_limit = per_instance_cost_limit


class DummyAgentConfig:
    def __init__(self, model):
        self.model = model

    def model_copy(self, deep=False):
        # mimic pydantic-like copy behavior returning a shallow clone for testing
        # keep same model object so we can observe mutation
        return self


class DummyRetryLoopConfig:
    def __init__(self, cost_limit):
        self.cost_limit = cost_limit


class DummyTotalInstanceStats:
    def __init__(self, instance_cost):
        self.instance_cost = instance_cost


class DummyConfig:
    def __init__(self, agent_configs, retry_loop):
        self.agent_configs = agent_configs
        self.retry_loop = retry_loop


class DummyLogger:
    def __init__(self):
        self.debug_calls = []

    def debug(self, msg, *args, **kwargs):
        # capture debug messages for assertions
        self.debug_calls.append((msg, args, kwargs))


def _bind_and_call_setup(fake_self):
    # bind the function object from the real RetryAgent class to our fake instance
    func = agents.RetryAgent._setup_agent
    bound = types.MethodType(func, fake_self)
    return bound()


def test_setup_agent_budget_exhausted_round_030(tmp_path, monkeypatch):
    """
    Case: remaining_budget < agent_config.model.per_instance_cost_limit
    Expect: per_instance_cost_limit set to remaining_budget, logger.debug called,
    hooks are attached, DefaultAgent.setup invoked with attempt-specific dir, and returned agent.
    """
    # Arrange
    remaining_budget = 3.5
    # initial per-instance limit is larger so assignment branch is taken
    model = DummyModel(per_instance_cost_limit=10.0)
    agent_config = DummyAgentConfig(model=model)
    cfg = DummyConfig(agent_configs=[agent_config], retry_loop=DummyRetryLoopConfig(cost_limit=10.0))

    fake_self = types.SimpleNamespace()
    fake_self.config = cfg
    fake_self._i_attempt = 1
    fake_self._total_instance_stats = DummyTotalInstanceStats(instance_cost=6.5)  # makes remaining 3.5

    # prepare a hook object and ensure _hooks contains it
    hook_obj = object()
    fake_self._hooks = [hook_obj]

    # output dir, env and problem_statement must not be None per asserts in function
    fake_self._output_dir = tmp_path
    fake_self._problem_statement = object()
    fake_self._env = object()

    # stub logger to capture debug messages
    fake_logger = DummyLogger()
    fake_self.logger = fake_logger

    # stub DefaultAgent.from_config to return our stub agent and capture the passed config
    created = {}

    def fake_from_config(passed_config):
        # record that the function was called with the derived agent_config
        created['passed_config'] = passed_config
        return _StubAgent()

    monkeypatch.setattr(agents.DefaultAgent, "from_config", staticmethod(fake_from_config))

    # Act
    returned_agent = _bind_and_call_setup(fake_self)

    # Assert
    # 1) DefaultAgent.from_config received the agent_config copy
    assert created.get('passed_config') is agent_config

    # 2) The model per_instance_cost_limit was adjusted down to remaining budget
    assert agent_config.model.per_instance_cost_limit == pytest.approx(remaining_budget)

    # 3) Logger.debug was called at least once and recorded the remaining_budget
    assert fake_logger.debug_calls, "expected a debug call when budget is exhausted"
    # check message formatting contains 'remaining budget' message string fragment
    found = any('remaining budget' in call[0] for call in fake_logger.debug_calls)
    assert found, f"expected debug message mentioning 'remaining budget' but got {fake_logger.debug_calls}"

    # 4) Hooks were attached to the created agent
    assert isinstance(returned_agent, _StubAgent)
    assert returned_agent.added_hooks == [hook_obj]

    # 5) setup was called with environment, problem_statement and an output dir containing attempt index
    called = returned_agent.setup_called_with
    assert called is not None
    assert called["env"] is fake_self._env
    assert called["problem_statement"] is fake_self._problem_statement
    assert isinstance(called["output_dir"], Path)
    assert str(called["output_dir"]).endswith(f"attempt_{fake_self._i_attempt}"), called["output_dir"]


def test_setup_agent_budget_sufficient_no_hooks_round_030(tmp_path, monkeypatch):
    """
    Case: remaining_budget >= agent_config.model.per_instance_cost_limit and no hooks
    Expect: per_instance_cost_limit unchanged, logger.debug not called, no hooks attached,
    DefaultAgent.setup invoked and returned agent.
    """
    # Arrange
    # remaining budget is bigger than per-instance cost limit so no reassignment occurs
    model = DummyModel(per_instance_cost_limit=2.0)
    agent_config = DummyAgentConfig(model=model)
    cfg = DummyConfig(agent_configs=[agent_config], retry_loop=DummyRetryLoopConfig(cost_limit=10.0))

    fake_self = types.SimpleNamespace()
    fake_self.config = cfg
    fake_self._i_attempt = 2
    fake_self._total_instance_stats = DummyTotalInstanceStats(instance_cost=5.0)  # remaining 5.0

    # no hooks present -> loop should not call add_hook
    fake_self._hooks = []

    fake_self._output_dir = tmp_path
    fake_self._problem_statement = object()
    fake_self._env = object()

    fake_logger = DummyLogger()
    fake_self.logger = fake_logger

    created = {}

    def fake_from_config(passed_config):
        created['passed_config'] = passed_config
        return _StubAgent()

    monkeypatch.setattr(agents.DefaultAgent, "from_config", staticmethod(fake_from_config))

    # Act
    returned_agent = _bind_and_call_setup(fake_self)

    # Assert
    # DefaultAgent.from_config called
    assert created.get('passed_config') is agent_config

    # per_instance_cost_limit unchanged
    assert agent_config.model.per_instance_cost_limit == 2.0

    # Logger.debug should not have the 'remaining budget' debug call
    found = any('remaining budget' in call[0] for call in fake_logger.debug_calls)
    assert not found, "did not expect a remaining-budget debug message when budget is sufficient"

    # No hooks attached
    assert isinstance(returned_agent, _StubAgent)
    assert returned_agent.added_hooks == []

    # setup called with expected args
    called = returned_agent.setup_called_with
    assert called is not None
    assert called["env"] is fake_self._env
    assert called["problem_statement"] is fake_self._problem_statement
    assert str(called["output_dir"]).endswith(f"attempt_{fake_self._i_attempt}"), called["output_dir"]
