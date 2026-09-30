import pytest
from types import SimpleNamespace
from sweagent.agent.models import HumanModel

# Tests exercise HumanModel.query behavior by calling the underlying function
# with a fake `self` that exposes a controllable `_query` method. This avoids
# instantiating the real HumanModel and keeps tests deterministic.

def test_keyboardinterrupt_round_031(capsys):
    """Simulate KeyboardInterrupt on first _query call, then a normal return.

    Expectation:
    - The first call to _query raises KeyboardInterrupt which triggers the
      except branch that prints the caret message and then calls self.query;
      provide a fake `query` method on the fake object to return the final
      value (avoid AttributeError and infinite recursion).
    - The printed message for KeyboardInterrupt is observable on stdout.
    """
    class Fake:
        def __init__(self):
            self.calls = 0
        def _query(self, history, action_prompt):
            # First call: simulate user pressing Ctrl-C
            if self.calls == 0:
                self.calls += 1
                raise KeyboardInterrupt
            # Subsequent call (not used in this setup): return a predictable value
            return {"message": "ok-after-cancel"}
        def query(self, history, action_prompt, n=None, **kwargs):
            # Provide a concrete query method so HumanModel.query's recursive
            # call to self.query succeeds and returns a deterministic value.
            return {"message": "ok-after-cancel"}

    fake = Fake()
    # Call the class function directly with our fake self
    result = HumanModel.query(fake, history=[], action_prompt="> ")

    # The function should return the inner successful result provided by
    # fake.query
    assert result == {"message": "ok-after-cancel"}

    # And the KeyboardInterrupt branch prints the expected prompt hint
    captured = capsys.readouterr()
    assert "^C (exit with ^D)" in captured.out


def test_eoferror_with_n_round_031(capsys):
    """When _query raises EOFError repeatedly and n is provided, expect a
    list of exit messages and a printed Goodbye message.
    """
    class FakeExit:
        def __init__(self):
            self.calls = 0
        def _query(self, history, action_prompt):
            # Always simulate EOF (user pressed Ctrl-D / EOF)
            self.calls += 1
            raise EOFError

    fake = FakeExit()
    # Request 2 samples; expect two appended exit messages
    result = HumanModel.query(fake, history=[], action_prompt="> ", n=2)

    assert isinstance(result, list)
    assert result == [{"message": "exit"}, {"message": "exit"}]

    captured = capsys.readouterr()
    # The EOFError branch prints a Goodbye message (may include a leading newline)
    assert "Goodbye!" in captured.out


def test_multiple_samples_round_031():
    """Verify that when n > 1, multiple calls to _query produce a list of
    corresponding results and are returned as a list (no collapse to single
    item).
    """
    class FakeMulti:
        def __init__(self):
            self.i = 0
        def _query(self, history, action_prompt):
            # Return deterministic, distinct dicts per call
            val = {"message": f"item-{self.i}"}
            self.i += 1
            return val

    fake = FakeMulti()
    result = HumanModel.query(fake, history=[], action_prompt="> ", n=3)

    assert isinstance(result, list)
    assert result == [
        {"message": "item-0"},
        {"message": "item-1"},
        {"message": "item-2"},
    ]
