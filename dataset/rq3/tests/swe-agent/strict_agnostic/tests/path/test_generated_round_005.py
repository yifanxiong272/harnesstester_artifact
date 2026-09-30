import builtins
from types import SimpleNamespace
import pytest

# Import the class to get the bound function object. We will not construct a full
# HumanModel via its constructor; instead we bind the _query function to a
# lightweight dummy object that provides only the attributes/methods used by
# _query. This avoids side effects and external dependencies.
from sweagent.agent.models import HumanModel


class FakeInput:
    """Callable used to monkeypatch builtins.input with a deterministic
    sequence of responses. Raises AssertionError if more calls are made than
    responses provided to make tests deterministic.
    """

    def __init__(self, responses):
        self._iter = iter(responses)

    def __call__(self, prompt=""):
        try:
            return next(self._iter)
        except StopIteration:
            raise AssertionError(f"No more input responses for prompt: {prompt!r}")


class DummySelf:
    """A minimal object that exposes the attributes and methods accessed by
    HumanModel._query. Uses simple flags to allow observable assertions.
    """

    def __init__(self, multi_line_command_endings=None):
        if multi_line_command_endings is None:
            multi_line_command_endings = {}
        self.multi_line_command_endings = dict(multi_line_command_endings)
        self.saved = False
        self.updated = False
        # Stats object with instance_cost attribute used in spend_money branch
        self.stats = SimpleNamespace(instance_cost=0.0)

    def _save_readline_history(self):
        # record that this was called
        self.saved = True

    def _update_stats(self):
        # record that this was called
        self.updated = True


def call_query_with_input_sequence(dummy, input_sequence, action_prompt="> "):
    """Helper to monkeypatch builtins.input with FakeInput for the duration
    of a single call to HumanModel._query bound to dummy.

    Important: assign dummy._query to the bound method so that recursive calls
    inside HumanModel._query (self._query(...)) resolve correctly to the same
    bound function. Without this, recursion fails with AttributeError on
    dummy._query.
    """
    fake = FakeInput(input_sequence)
    original_input = builtins.input
    builtins.input = fake
    try:
        # Bind the function defined on the class to our dummy instance
        bound = HumanModel._query.__get__(dummy, HumanModel)
        # Ensure recursive calls (self._query(...)) inside _query resolve
        # properly by attaching the bound method onto the dummy instance.
        dummy._query = bound
        return bound(history=None, action_prompt=action_prompt)
    finally:
        builtins.input = original_input


def test_multiline_command_round_005():
    """Exercise the multi-line command branch (command in
    multi_line_command_endings). The test asserts that:
    - _save_readline_history was called
    - _update_stats was called
    - the returned message is the newline-joined buffer
    """
    dummy = DummySelf(multi_line_command_endings={"edit": "END"})

    # Sequence of inputs: initial action, then lines inside the multi-line
    # input, ending with the end keyword. These responses are returned in
    # order by patched input().
    inputs = [
        "edit filename.txt",
        "first line of content",
        "END",
    ]

    result = call_query_with_input_sequence(dummy, inputs, action_prompt="> ")

    # Expected message is the newline-joined buffer (initial + subsequent lines)
    expected_message = "edit filename.txt\nfirst line of content\nEND"
    assert isinstance(result, dict), "Expected a dict result"
    assert result.get("message") == expected_message

    # Ensure side-effect methods were invoked
    assert dummy.saved is True, "_save_readline_history should have been called"
    assert dummy.updated is True, "_update_stats should have been called"


def test_start_multiline_recursive_spend_round_005():
    """Exercise the start_multiline_command recursion and then the spend_money
    branch. Behavior asserted:
    - When the outer multi-line flow sees the immediate end keyword, it
      returns by calling _query recursively.
    - The inner call processes a spend_money command, increments
      stats.instance_cost, and returns the transformed echo message.
    """
    dummy = DummySelf(multi_line_command_endings={})

    # Inputs for the entire sequence of calls to input():
    # 1) Outer call: initial action -> 'start_multiline_command'
    # 2) Outer loop: returns 'end_multiline_command' which triggers an inner
    #    recursive call to _query
    # 3) Inner call: provide a spend_money command to exercise the spend branch
    inputs = [
        "start_multiline_command",
        "end_multiline_command",
        "spend_money 12.5",
    ]

    result = call_query_with_input_sequence(dummy, inputs, action_prompt="> ")

    # After handling spend_money 12.5, stats.instance_cost should be incremented
    assert abs(dummy.stats.instance_cost - 12.5) < 1e-12

    # The returned message should be the echo set by the spend_money branch
    assert isinstance(result, dict)
    assert result.get("message") == "echo 'Spent 12.5 dollars'"

    # Ensure that _save_readline_history and _update_stats were invoked at least
    # during the inner call
    assert dummy.saved is True
    assert dummy.updated is True
