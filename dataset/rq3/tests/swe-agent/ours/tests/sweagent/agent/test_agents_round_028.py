import types
from pathlib import Path
import pytest

from sweagent.agent import agents


class _DummyModel:
    def __init__(self, per_instance_cost_limit):
        self.per_instance_cost_limit = per_instance_cost_limit


class _AgentConfigItem:
    """Minimal object that implements model_copy(deep=True) used by RetryAgent._setup_agent."""

    def __init__(self, model_per_instance_cost_limit):
        # store an inner model object to be returned by model_copy
        self._model = _DummyModel(model_per_instance_cost_limit)

    def model_copy(self, deep: bool = True):
        # return a new object that has attribute `model` expected by code
        o = types.SimpleNamespace()
        # copy the model object so tests can observe side-effects on the returned object
        o.model = _DummyModel(self._model.per_instance_cost_limit)
        return o


class _FakeAgent:
    def __init__(self):
        self.added_hooks = []
        self.setup_called_with = None

    def add_hook(self, hook):
        self.added_hooks.append(hook)

    def setup(self, env, problem_statement, output_dir):
        # record call for assertions
        self.setup_called_with = (env, problem_statement, output_dir)


class _FakeLogger:
    def __init__(self):
        self.debug_calls = []

    def debug(self, *args, **kwargs):
        self.debug_calls.append((args, kwargs))


class _SimpleRetryLoop:
    def __init__(self, cost_limit):
        self.cost_limit = cost_limit


class _TotalStats:
    def __init__(self, instance_cost):
        self.instance_cost = instance_cost


def _make_minimal_retry_agent_instance():
    # Create an uninitialized RetryAgent instance and set the minimal attributes
    ra = object.__new__(agents.RetryAgent)
    return ra


def test_setup_agent_sets_cost_and_adds_hooks_round_028(monkeypatch):
    """Trigger branch where remaining_budget < per_instance_cost_limit and _hooks non-empty.

    Assertions:
    - logger.debug is invoked
    - hooks are added to the created agent
    - agent.setup is called with env/problem_statement/output_dir
    """
    # Arrange
    fake_agent = _FakeAgent()
    # Patch DefaultAgent.from_config where the module resolves it
    monkeypatch.setattr(agents.DefaultAgent, "from_config", staticmethod(lambda cfg: fake_agent))

    # Override the class attribute for _total_instance_stats (property is read-only)
    monkeypatch.setattr(agents.RetryAgent, "_total_instance_stats", _TotalStats(instance_cost=1), raising=False)

    ra = _make_minimal_retry_agent_instance()

    # Create config with one agent_config whose model_copy returns model.per_instance_cost_limit = 10
    config_item = _AgentConfigItem(model_per_instance_cost_limit=10)
    # Set retry loop cost_limit small so remaining_budget < 10
    ra.config = types.SimpleNamespace(agent_configs=[config_item], retry_loop=_SimpleRetryLoop(cost_limit=3))

    ra._i_attempt = 0
    ra._hooks = ["hook-a", "hook-b"]
    # required asserts in code: not None
    ra._output_dir = Path("/tmp")
    ra._problem_statement = object()
    ra._env = object()

    # Provide a logger that records debug calls
    fake_logger = _FakeLogger()
    ra.logger = fake_logger

    # Act
    returned = agents.RetryAgent._setup_agent(ra)

    # Assert returned is the fake agent
    assert returned is fake_agent

    # Validate that logger.debug was called at least once indicating the budget branch executed
    assert len(fake_logger.debug_calls) >= 1

    # Validate hooks were added to the fake agent
    assert fake_agent.added_hooks == ["hook-a", "hook-b"]

    # Validate setup was called with expected arguments (env, problem_statement, output_dir path ending with attempt_0)
    assert fake_agent.setup_called_with is not None
    env_arg, ps_arg, out_dir_arg = fake_agent.setup_called_with
    assert env_arg is ra._env
    assert ps_arg is ra._problem_statement
    assert isinstance(out_dir_arg, Path)
    assert out_dir_arg.name == f"attempt_{ra._i_attempt}"


def test_setup_agent_preserves_cost_and_skips_hooks_round_028(monkeypatch):
    """Trigger branch where remaining_budget >= per_instance_cost_limit and _hooks is empty.

    Assertions:
    - logger.debug is not invoked
    - no hooks are added
    - agent.setup is called
    """
    fake_agent = _FakeAgent()
    monkeypatch.setattr(agents.DefaultAgent, "from_config", staticmethod(lambda cfg: fake_agent))

    # Override the class attribute for _total_instance_stats so remaining_budget = 7 - 2 = 5
    monkeypatch.setattr(agents.RetryAgent, "_total_instance_stats", _TotalStats(instance_cost=2), raising=False)

    ra = _make_minimal_retry_agent_instance()

    # Make model per-instance cost limit small (2) and remaining budget larger (5)
    config_item = _AgentConfigItem(model_per_instance_cost_limit=2)
    ra.config = types.SimpleNamespace(agent_configs=[config_item], retry_loop=_SimpleRetryLoop(cost_limit=7))

    ra._i_attempt = 1
    # empty hooks to cover skip branch
    ra._hooks = []
    ra._output_dir = Path("/var/tmp")
    ra._problem_statement = object()
    ra._env = object()

    fake_logger = _FakeLogger()
    ra.logger = fake_logger

    # Act
    returned = agents.RetryAgent._setup_agent(ra)

    # Assert returned is fake agent
    assert returned is fake_agent

    # logger.debug should not have been called in this path
    assert fake_logger.debug_calls == []

    # No hooks were added since ra._hooks was empty
    assert fake_agent.added_hooks == []

    # Setup was still called
    assert fake_agent.setup_called_with is not None
    env_arg, ps_arg, out_dir_arg = fake_agent.setup_called_with
    assert env_arg is ra._env
    assert ps_arg is ra._problem_statement
    assert out_dir_arg.name == f"attempt_{ra._i_attempt}"
