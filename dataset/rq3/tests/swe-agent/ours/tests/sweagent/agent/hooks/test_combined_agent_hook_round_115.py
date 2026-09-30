import sys
import types
import importlib
import pytest

# Ensure a minimal sweagent.types module exists so importing the target module is safe
if 'sweagent.types' not in sys.modules:
    _types_mod = types.ModuleType('sweagent.types')

    # Minimal stand-ins for the real types used by the hooks module.
    class AgentInfo:
        """Minimal stand-in for AgentInfo used only for import resolution in tests."""
        def __init__(self, name: str = "agent"):
            self.name = name

    class StepOutput:
        """Minimal stand-in for the real StepOutput."""
        def __init__(self, data=None):
            self.data = data

    class Trajectory:
        """Minimal stand-in for Trajectory."""
        def __init__(self, steps=None):
            self.steps = list(steps or [])

    _types_mod.AgentInfo = AgentInfo
    _types_mod.StepOutput = StepOutput
    _types_mod.Trajectory = Trajectory
    sys.modules['sweagent.types'] = _types_mod

# Import the module under test after ensuring its type dependency is available.
from sweagent.agent.hooks import abstract as abstract_hooks

CombinedAgentHook = abstract_hooks.CombinedAgentHook


class HookRecorder:
    """Simple hook object that records calls to on_action_started."""
    def __init__(self):
        self.called = False
        self.calls = []

    def on_action_started(self, *args, **kwargs):
        # Record that this hook was invoked and the exact call shape
        self.called = True
        self.calls.append((args, kwargs))


def test_on_action_started_calls_each_hook_round_115():
    """Verify that CombinedAgentHook forwards the named 'step' argument to every hook."""
    h1 = HookRecorder()
    h2 = HookRecorder()

    combined = CombinedAgentHook(hooks=[h1, h2])

    # Use a unique sentinel object as the step so identity can be asserted
    step_sentinel = object()

    # Call using the required keyword-only parameter
    result = combined.on_action_started(step=step_sentinel)

    # The combined hook method is expected to return None and call each hook
    assert result is None

    # Both hooks should have been called exactly once
    assert h1.called is True
    assert h2.called is True
    assert len(h1.calls) == 1
    assert len(h2.calls) == 1

    # The hooks must receive the 'step' as a keyword argument and no positional args
    args1, kwargs1 = h1.calls[0]
    args2, kwargs2 = h2.calls[0]
    assert args1 == ()
    assert args2 == ()
    assert 'step' in kwargs1 and kwargs1['step'] is step_sentinel
    assert 'step' in kwargs2 and kwargs2['step'] is step_sentinel


def test_on_action_started_with_empty_hooks_round_115():
    """Calling on_action_started with no hooks should be a no-op (no exception, returns None)."""
    combined = CombinedAgentHook(hooks=[])
    step_sentinel = object()

    # Should not raise and should return None
    result = combined.on_action_started(step=step_sentinel)
    assert result is None


def test_on_action_started_requires_keyword_only_round_115():
    """Verify that the method enforces the keyword-only 'step' parameter (positional call -> TypeError)."""
    combined = CombinedAgentHook(hooks=[])

    # Calling with a positional argument should raise a TypeError due to the signature using '*,'
    with pytest.raises(TypeError):
        combined.on_action_started(object())
