import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.agents')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Test that _setup_agent adjusts the agent model's per_instance_cost_limit
        when remaining_budget is smaller than the configured per_instance_cost_limit.
        """
        # Create minimal dummy config/model objects that mimic the real API used in _setup_agent
        class DummyModelConfig:
            def __init__(self, per_instance_cost_limit: float):
                self.per_instance_cost_limit = per_instance_cost_limit

            def model_copy(self, deep: bool = False):
                return DummyModelConfig(self.per_instance_cost_limit)

        class DummyAgentConfig:
            def __init__(self, per_instance_cost_limit: float):
                self.model = DummyModelConfig(per_instance_cost_limit)

            def model_copy(self, deep: bool = False):
                return DummyAgentConfig(self.model.per_instance_cost_limit)

        class DummyRetryLoop:
            def __init__(self, cost_limit: float):
                self.cost_limit = cost_limit

        class DummyConfig:
            def __init__(self, agent_configs, retry_loop):
                self.agent_configs = agent_configs
                self.retry_loop = retry_loop

            def model_copy(self, deep: bool = False):
                # return a shallow copy adequate for the test
                return DummyConfig([ac.model_copy(deep=deep) for ac in self.agent_configs], self.retry_loop)

        # Simple addable stats object so _total_instance_stats property can compute instance_cost
        class AddableStats:
            def __init__(self, instance_cost: float = 0.0):
                self.instance_cost = instance_cost

            def __add__(self, other):
                return AddableStats(self.instance_cost + getattr(other, "instance_cost", 0.0))

            def model_dump(self):
                return {"instance_cost": self.instance_cost}

        class DummyRloop:
            def __init__(self, review_model_stats):
                self.review_model_stats = review_model_stats

        # Prepare a config where the agent per-instance limit is larger than remaining budget
        initial_per_instance_limit = 100.0
        total_cost_limit = 30.0  # small total cost limit to force adjustment
        dummy_agent_cfg = DummyAgentConfig(per_instance_cost_limit=initial_per_instance_limit)
        dummy_config = DummyConfig(agent_configs=[dummy_agent_cfg], retry_loop=DummyRetryLoop(cost_limit=total_cost_limit))

        # Instantiate the RetryAgent with our dummy config
        ra = RetryAgent.from_config(dummy_config)

        # Provide attributes so the _total_instance_stats property works:
        # set the attempt stats and a rloop with review_model_stats so addition yields instance_cost 0.0
        ra._total_instance_attempt_stats = AddableStats(0.0)
        ra._rloop = DummyRloop(review_model_stats=AddableStats(0.0))

        # Provide the attributes that _setup_agent asserts exist (these will not be used because we stub DefaultAgent)
        ra._output_dir = Path(".")
        ra._problem_statement = object()
        ra._env = object()

        # Monkeypatch DefaultAgent.from_config to capture the passed config and return a dummy agent.
        captured = {}

        class DummyAgent:
            def add_hook(self, hook):
                pass

            def setup(self, env, problem_statement, output_dir):
                # do nothing
                pass

        original_from_config = DefaultAgent.from_config
        try:
            def fake_from_config(cfg):
                # capture the config passed in for assertions
                captured["cfg"] = cfg
                return DummyAgent()

            DefaultAgent.from_config = staticmethod(fake_from_config)
            # Call the method under test
            returned_agent = ra._setup_agent()

            # Ensure DefaultAgent.from_config was called and we got our DummyAgent back
            self.assertIsInstance(returned_agent, DummyAgent)

            # Assert that the agent_config's model.per_instance_cost_limit was adjusted to remaining_budget
            self.assertIn("cfg", captured)
            passed_cfg = captured["cfg"]
            self.assertAlmostEqual(passed_cfg.model.per_instance_cost_limit, total_cost_limit)
        finally:
            # restore original
            DefaultAgent.from_config = original_from_config
