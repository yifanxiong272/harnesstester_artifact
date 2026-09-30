# file: sweagent/agent/agents.py:707-719
# asked: {"lines": [717], "branches": [[716, 717]]}
# gained: {"lines": [717], "branches": [[716, 717]]}

import types
from types import SimpleNamespace

import pytest

from sweagent.agent.agents import DefaultAgent


class MinimalAgent(DefaultAgent):
    """
    Minimal stub of DefaultAgent that avoids running the real __init__
    but allows calling the inherited add_instance_template_to_history method.
    """

    def __init__(self, instance_template: str, strategy_template):
        # do not call DefaultAgent.__init__; provide only attributes used by the method
        self.history = [{"role": "system"}]
        self.templates = SimpleNamespace(instance_template=instance_template, strategy_template=strategy_template)
        self.name = "test-agent"
        # capture calls to the templating helper
        self._added_calls = []

        def _adder(templates, **kwargs):
            # mimic signature of the real method but only record inputs
            self._added_calls.append((list(templates), dict(kwargs)))

        self._add_templated_messages_to_history = _adder


def test_add_instance_template_appends_strategy_template():
    agent = MinimalAgent(instance_template="INSTANCE TEMPLATE", strategy_template="STRATEGY TEMPLATE")
    # Call with a state to ensure kwargs are forwarded
    state = {"file": "example.py", "line": "10"}
    agent.add_instance_template_to_history(state)

    # Ensure the helper was called exactly once
    assert len(agent._added_calls) == 1
    templates_passed, kwargs_passed = agent._added_calls[0]

    # Both instance and strategy templates should be present and in order
    assert templates_passed == ["INSTANCE TEMPLATE", "STRATEGY TEMPLATE"]
    # The state should have been forwarded as kwargs
    assert kwargs_passed == state


def test_add_instance_template_without_strategy_template():
    agent = MinimalAgent(instance_template="ONLY INSTANCE", strategy_template=None)
    state = {"a": "b"}
    agent.add_instance_template_to_history(state)

    assert len(agent._added_calls) == 1
    templates_passed, kwargs_passed = agent._added_calls[0]

    # Only the instance template should be present
    assert templates_passed == ["ONLY INSTANCE"]
    assert kwargs_passed == state
