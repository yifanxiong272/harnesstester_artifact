import pytest

from sweagent.agent.hooks.abstract import CombinedAgentHook


class RecordingHook:
    """A deterministic, in-process fake hook that records calls.

    The on_actions_generated method accepts a keyword-only `step` to match
    the hook contract used by CombinedAgentHook.
    """

    def __init__(self, name, record_list):
        self.name = name
        self.record_list = record_list
        self.calls = []

    def on_actions_generated(self, *, step):
        # Record the exact object identity and the hook name in a shared list
        # so tests can assert ordering and argument forwarding.
        self.calls.append(step)
        self.record_list.append(self.name)


def test_single_hook_called_round_114():
    """CombinedAgentHook should call a single contained hook with the step kwarg.

    This verifies that line 81 (the hook invocation) is executed for at
    least one hook and that the forwarded argument is the same object.
    """
    call_order = []
    hook = RecordingHook("h1", call_order)

    # Use a plain dict as a StepOutput stand-in; CombinedAgentHook only forwards it.
    step_obj = {"step_id": 1, "actions": ["a"]}

    combined = CombinedAgentHook(hooks=[hook])
    result = combined.on_actions_generated(step=step_obj)

    # The function has no explicit return, so it should return None.
    assert result is None

    # The fake hook should have recorded the exact object passed.
    assert hook.calls == [step_obj]

    # The shared call_order should show the hook was invoked (by name).
    assert call_order == ["h1"]


def test_multiple_hooks_order_and_identity_round_114():
    """Verify multiple hooks are invoked in list order and receive the same step object.

    This ensures the loop body executes for each hook and the forwarded
    `step` object identity is preserved for each call.
    """
    call_order = []
    hook_a = RecordingHook("A", call_order)
    hook_b = RecordingHook("B", call_order)

    step_obj = ("unique-step", 42)  # immutable tuple to ensure identity is clear

    combined = CombinedAgentHook(hooks=[hook_a, hook_b])
    ret = combined.on_actions_generated(step=step_obj)

    assert ret is None

    # Both hooks should have recorded the same step object
    assert hook_a.calls == [step_obj]
    assert hook_b.calls == [step_obj]

    # The order of invocation should match the order in the list
    assert call_order == ["A", "B"]
