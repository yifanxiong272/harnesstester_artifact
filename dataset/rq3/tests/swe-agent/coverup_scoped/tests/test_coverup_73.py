# file: sweagent/agent/history_processors.py:13-16
# asked: {"lines": [16], "branches": []}
# gained: {"lines": [16], "branches": []}

import pytest
from sweagent.agent import history_processors
from sweagent.types import History


def test_abstract_history_processor_call_raises_not_implemented():
    # Call the unbound __call__ function on the Protocol class directly.
    # This should execute the method body and raise NotImplementedError.
    with pytest.raises(NotImplementedError):
        history_processors.AbstractHistoryProcessor.__call__(None, [])  # type: ignore


def test_concrete_processor_can_be_called_and_returns_history():
    # A simple concrete "processor" that implements __call__ and returns the history unchanged.
    class ConcreteProcessor:
        def __call__(self, history: History) -> History:
            return history

    proc = ConcreteProcessor()
    sample_history: History = []
    result = proc(sample_history)
    assert result is sample_history or result == sample_history
