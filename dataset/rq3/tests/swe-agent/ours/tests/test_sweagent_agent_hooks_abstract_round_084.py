import pytest

from sweagent.agent.hooks.abstract import CombinedAgentHook


class HookSpy:
    def __init__(self):
        self.calls = []

    def on_init(self, agent):
        # record the exact agent object the CombinedAgentHook forwards
        self.calls.append(agent)


def test_on_init_no_hooks_round_084():
    """When CombinedAgentHook has no hooks, on_init should be a no-op (no errors).

    This covers the branch where the for-loop does not iterate.
    """
    combined = CombinedAgentHook(hooks=[])  # empty list -> loop should not run
    sentinel = object()

    # should not raise and nothing to assert beyond existence; ensure attribute present
    combined.on_init(agent=sentinel)

    # verify hooks property remains empty (sanity, observable behavior)
    assert list(combined.hooks) == []


def test_on_init_calls_each_hook_round_084():
    """Ensure CombinedAgentHook forwards the agent keyword to each hook's on_init.

    This covers the branch where the for-loop iterates and calls hook.on_init(agent=agent).
    """
    spy1 = HookSpy()
    spy2 = HookSpy()
    combined = CombinedAgentHook(hooks=[spy1, spy2])

    sentinel_agent = object()
    combined.on_init(agent=sentinel_agent)

    # Both spies should have been called exactly once with the same sentinel object
    assert spy1.calls == [sentinel_agent]
    assert spy2.calls == [sentinel_agent]
