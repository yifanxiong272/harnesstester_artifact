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
        """Ensure that RetryAgent._setup_agent adds all hooks to the created sub-agent."""
        # Minimal dummy classes to satisfy RetryAgent expectations
        class _Model:
            def __init__(self):
                self.per_instance_cost_limit = 100

        class DummyAgentConfig:
            def __init__(self):
                self.model = _Model()

            def model_copy(self, deep=True):
                return self

        class DummyRetryConfig:
            def __init__(self):
                self.agent_configs = [DummyAgentConfig()]
                # retry_loop with a cost_limit attribute
                self.retry_loop = type("RL", (), {"cost_limit": 1000})()

            def model_copy(self, deep=True):
                return self

        class DummyProblemStatement:
            id = "dummy"

            def get_problem_statement(self):
                return "problem"

            def get_extra_fields(self):
                return {}

        # Fake agent that records add_hook calls and setup invocation
        class FakeAgent:
            def __init__(self):
                self.added_hooks = []
                self.setup_called = False

            def add_hook(self, hook):
                self.added_hooks.append(hook)

            def setup(self, env, problem_statement, output_dir):
                self.setup_called = True

        # Instantiate RetryAgent with the dummy config
        ra = RetryAgent(DummyRetryConfig())

        # Prepare hooks list and required attributes for _setup_agent
        hook_a = object()
        hook_b = object()
        ra._hooks = [hook_a, hook_b]
        ra._output_dir = Path(".")
        ra._problem_statement = DummyProblemStatement()
        ra._env = object()

        # Provide a compatible _rloop so that the _total_instance_stats property works
        # (InstanceStats is part of the project and available in the test environment)
        ra._rloop = type("RLoop", (), {"review_model_stats": InstanceStats()})()

        fake_agent = FakeAgent()

        # Patch DefaultAgent.from_config to return our fake agent so that the loop runs
        with patch.object(DefaultAgent, "from_config", return_value=fake_agent):
            result_agent = ra._setup_agent()

        # Assertions: returned agent is our fake agent and add_hook was called for each hook
        self.assertIs(result_agent, fake_agent)
        self.assertEqual(fake_agent.added_hooks, [hook_a, hook_b])
        self.assertTrue(fake_agent.setup_called)
