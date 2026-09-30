import types
import pytest

from sweagent.agent import agents

# We will call the unbound function RetryAgent.add_hook with a lightweight
# dummy 'self' that provides the attributes used by the method. This avoids
# instantiating the full RetryAgent (which may require heavy dependencies)
# while still executing the exact lines in the real source.

class DummyChook:
    def __init__(self):
        self.calls = []

    def add_hook(self, hook):
        # record the hook; used to assert the call happened
        self.calls.append(hook)


def test_retry_agent_add_hook_happy_round_111():
    # Prepare a dummy self object with the attributes the method uses.
    dummy = types.SimpleNamespace()
    dummy._chook = DummyChook()
    dummy._hooks = []

    # A sentinel hook object (shape is preserved but no particular interface required)
    sentinel_hook = object()

    # Call the unbound function from the real class definition to execute
    # the actual source lines in sweagent.agent.agents
    agents.RetryAgent.add_hook(dummy, sentinel_hook)

    # Assertions (observable behavior): the combined hook received the hook
    # and the local _hooks list was appended with the same object.
    assert dummy._chook.calls == [sentinel_hook]
    assert dummy._hooks == [sentinel_hook]


def test_retry_agent_add_hook_propagates_and_does_not_append_on_error_round_111():
    # If the underlying combined hook raises, the append should not happen
    class FailingChook:
        def add_hook(self, hook):
            raise RuntimeError("boom")

    dummy = types.SimpleNamespace()
    dummy._chook = FailingChook()
    dummy._hooks = []

    sentinel_hook = object()

    # Ensure the exception is propagated and that _hooks remains unchanged
    with pytest.raises(RuntimeError, match="boom"):
        agents.RetryAgent.add_hook(dummy, sentinel_hook)

    assert dummy._hooks == []
