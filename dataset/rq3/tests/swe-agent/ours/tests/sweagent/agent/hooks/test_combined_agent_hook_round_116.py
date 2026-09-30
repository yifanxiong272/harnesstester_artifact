from sweagent.agent.hooks.abstract import CombinedAgentHook


class DummyHook:
    def __init__(self):
        self.calls = []

    def on_action_executed(self, *, step):
        # record the exact object received to assert identity/payload preservation
        self.calls.append(step)


def test_single_hook_called_round_116():
    """Ensure a single hook in CombinedAgentHook is invoked with the exact step kwarg."""
    dummy = DummyHook()
    combined = CombinedAgentHook(hooks=[dummy])

    step_obj = object()
    combined.on_action_executed(step=step_obj)

    assert dummy.calls == [step_obj]


def test_multiple_hooks_called_in_order_round_116():
    """Ensure multiple hooks are each invoked once and in the provided order with the same step object."""
    h1 = DummyHook()
    h2 = DummyHook()
    combined = CombinedAgentHook(hooks=[h1, h2])

    step_obj = object()
    combined.on_action_executed(step=step_obj)

    assert h1.calls == [step_obj]
    assert h2.calls == [step_obj]
