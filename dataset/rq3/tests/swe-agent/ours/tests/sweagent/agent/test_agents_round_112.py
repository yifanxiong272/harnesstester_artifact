import types
import pytest

import sweagent.agent.agents as agents


def _bind_method_to_obj(method, obj):
    """Bind an unbound function (descriptor) to a simple object instance.
    This avoids constructing the full DefaultAgent while still exercising
    the actual method implementation defined on DefaultAgent.
    """
    return method.__get__(obj, agents.DefaultAgent)


def test_add_instance_template_to_history_without_strategy_round_112():
    # Prepare a minimal fake instance with the attributes the method reads/writes
    dummy = types.SimpleNamespace()

    # history must satisfy the assertion in the method
    dummy.history = [{"role": "system"}]

    # templates object with instance_template set and strategy_template None
    dummy.templates = types.SimpleNamespace(instance_template="INST_TPL", strategy_template=None)

    # Capture calls to _add_templated_messages_to_history
    captured = []

    def fake_add_templated_messages_to_history(templates, **state):
        # record copies for deterministic assertions
        captured.append((list(templates), dict(state)))

    dummy._add_templated_messages_to_history = fake_add_templated_messages_to_history

    # Bind and call the real method implementation from the module
    bound = _bind_method_to_obj(agents.DefaultAgent.add_instance_template_to_history, dummy)

    # pass an example state dict; method should forward it to the internal call
    state = {"k": "v"}
    bound(state)

    # Assertions: method should call internal helper exactly once with only the instance template
    assert len(captured) == 1, "expected one call to _add_templated_messages_to_history"
    called_templates, called_state = captured[0]
    assert called_templates == ["INST_TPL"], "expected only the instance_template when strategy_template is None"
    assert called_state == state


def test_add_instance_template_to_history_with_strategy_round_112():
    # Another dummy instance where strategy_template is present to hit the branch
    dummy = types.SimpleNamespace()
    dummy.history = [{"role": "system"}]
    dummy.templates = types.SimpleNamespace(instance_template="INST_TPL", strategy_template="STRAT_TPL")

    captured = []

    def fake_add_templated_messages_to_history(templates, **state):
        captured.append((list(templates), dict(state)))

    dummy._add_templated_messages_to_history = fake_add_templated_messages_to_history

    bound = _bind_method_to_obj(agents.DefaultAgent.add_instance_template_to_history, dummy)

    state = {"alpha": 1}
    bound(state)

    # Assertions: should include both instance and strategy templates when strategy_template is not None
    assert len(captured) == 1
    called_templates, called_state = captured[0]
    assert called_templates == ["INST_TPL", "STRAT_TPL"]
    assert called_state == state
