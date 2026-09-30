# file: sweagent/agent/models.py:406-421
# asked: {"lines": [408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421], "branches": [[410, 411], [410, 419], [419, 420], [419, 421]]}
# gained: {"lines": [408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421], "branches": [[410, 411], [410, 419], [419, 420], [419, 421]]}

import types
from types import MethodType

import pytest

from sweagent.agent.models import HumanModel


def make_instance_with__query(fn):
    """
    Helper to create a HumanModel instance without calling __init__,
    and bind a custom _query method (as a bound method).
    """
    inst = object.__new__(HumanModel)
    inst._query = MethodType(fn, inst)
    return inst


def test_query_returns_single_and_multiple():
    # _query returns a dict echoing the action_prompt
    def _query(self, history, action_prompt):
        return {"echo": action_prompt}

    inst = make_instance_with__query(_query)

    # When n is None should return a single dict (not a list)
    result_single = inst.query(history=None, action_prompt="> single", n=None)
    assert isinstance(result_single, dict)
    assert result_single == {"echo": "> single"}

    # When n is provided should return a list of length n
    result_list = inst.query(history=None, action_prompt="> multi", n=3)
    assert isinstance(result_list, list)
    assert len(result_list) == 3
    assert all(item == {"echo": "> multi"} for item in result_list)


def test_query_keyboardinterrupt_recovers_and_prints(capsys):
    # First call raises KeyboardInterrupt, second call succeeds
    state = {"calls": 0}

    def _query(self, history, action_prompt):
        state["calls"] += 1
        if state["calls"] == 1:
            raise KeyboardInterrupt
        return {"ok": True, "calls": state["calls"]}

    inst = make_instance_with__query(_query)

    result = inst.query(history=None, action_prompt="> kb", n=None)

    # Should have called _query twice (one to raise, one to return)
    assert state["calls"] == 2
    # The method should return the successful dict (since n is None)
    assert result == {"ok": True, "calls": 2}

    captured = capsys.readouterr()
    # Ensure the KeyboardInterrupt branch printed the expected message
    assert "^C (exit with ^D)" in captured.out


def test_query_eoferror_returns_exit_message_and_handles_list_and_single(capsys):
    # Case 1: _query always raises EOFError -> should return {"message": "exit"} and print Goodbye!
    def _query_always_eof(self, history, action_prompt):
        raise EOFError

    inst1 = make_instance_with__query(_query_always_eof)

    result = inst1.query(history=None, action_prompt="> eof", n=None)
    assert result == {"message": "exit"}
    captured = capsys.readouterr()
    # "\nGoodbye!" is printed by the EOFError branch
    assert "Goodbye!" in captured.out

    # Case 2: first call returns, second call raises EOFError, with n=2 should return list
    seq = {"calls": 0}

    def _query_mixed(self, history, action_prompt):
        seq["calls"] += 1
        if seq["calls"] == 1:
            return {"first": True}
        raise EOFError

    inst2 = make_instance_with__query(_query_mixed)

    result_list = inst2.query(history=None, action_prompt="> mixed", n=2)
    # Should get a list with first dict and exit dict
    assert isinstance(result_list, list)
    assert result_list == [{"first": True}, {"message": "exit"}]
    # also ensure we attempted two calls
    assert seq["calls"] == 2
