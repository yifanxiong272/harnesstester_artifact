# file: sweagent/agent/agents.py:965-1018
# asked: {"lines": [978, 991, 992, 993, 994, 995, 997, 999], "branches": [[977, 978], [990, 991]]}
# gained: {"lines": [978, 991, 992, 993, 994, 995, 997, 999], "branches": [[977, 978], [990, 991]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.agents import DefaultAgent, _TotalExecutionTimeExceeded


def test_forward_raises_total_execution_time_exceeded():
    # Create a DefaultAgent instance without calling __init__
    agent = object.__new__(DefaultAgent)
    # Set total execution time above the tools.config.total_execution_timeout to trigger the exception
    agent._total_execution_time = 10.0
    agent.tools = SimpleNamespace(config=SimpleNamespace(total_execution_timeout=1.0))
    # Call forward and expect the internal control-flow exception
    with pytest.raises(_TotalExecutionTimeExceeded):
        agent.forward([])


def test_forward_uses_action_sampler_branch_and_updates_extra_info():
    # Prepare an agent instance bypassing __init__
    agent = object.__new__(DefaultAgent)
    # Ensure we do not hit the total execution time check
    agent._total_execution_time = 0.0
    # Minimal tools with a parse_actions callable
    agent.tools = SimpleNamespace(config=SimpleNamespace(total_execution_timeout=1.0))
    agent.tools.parse_actions = lambda output: ("thought_text", "action_text")

    # Hook that records calls
    class Hook:
        def __init__(self):
            self.model_query_called = False
            self.actions_generated_called = False

        def on_model_query(self, messages, agent=None):
            self.model_query_called = True

        def on_actions_generated(self, step):
            self.actions_generated_called = True

    hook = Hook()
    agent._chook = hook

    # Action sampler that returns a "best" with completion and extra_info
    best = SimpleNamespace(completion={"message": "sampler message"}, extra_info={"from_sampler": "yes"})
    agent._action_sampler = SimpleNamespace(get_action=lambda problem_statement, trajectory, history: best)

    # Satisfy assertion that _problem_statement is not None
    agent._problem_statement = SimpleNamespace()
    # Set internal trajectory storage used by the trajectory property
    agent._trajectory = []

    # Provide a name used when calling hooks
    agent.name = "test-agent"

    # Logger with an info method
    agent.logger = SimpleNamespace(info=lambda *args, **kwargs: None)

    # handle_action should return the step so we can inspect it
    agent.handle_action = lambda step: step

    # Run forward with a dummy history
    history = [{"role": "user", "content": "do something"}]
    step = agent.forward(history)

    # Assertions to verify behavior (covers the branch where _action_sampler is used)
    assert step.output == "sampler message"
    assert getattr(step, "extra_info", {}).get("from_sampler") == "yes"
    assert step.thought == "thought_text"
    assert step.action == "action_text"
    assert hook.model_query_called is True
    assert hook.actions_generated_called is True
