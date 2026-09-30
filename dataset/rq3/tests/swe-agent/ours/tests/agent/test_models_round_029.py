import builtins
import types
import pytest

from sweagent.agent import models

HumanModel = models.HumanModel


def _make_instance():
    # Avoid running __init__ (which may touch filesystem or readline).
    return object.__new__(HumanModel)


def test_query_returns_single_round_029(monkeypatch):
    instance = _make_instance()

    def fake_query(self, history, action_prompt):
        # simple deterministic single return
        return {"value": "single"}

    monkeypatch.setattr(HumanModel, "_query", fake_query)

    result = instance.query(history=None)
    assert isinstance(result, dict), "Expected a dict when n is None"
    assert result == {"value": "single"}


def test_query_returns_list_for_n_round_029(monkeypatch):
    instance = _make_instance()

    # prepare deterministic sequence of returns
    responses = [
        {"i": 0},
        {"i": 1},
        {"i": 2},
    ]

    def fake_query(self, history, action_prompt):
        # pop from front to ensure order and determinism
        return responses.pop(0)

    monkeypatch.setattr(HumanModel, "_query", fake_query)

    result = instance.query(history=None, n=3)
    assert isinstance(result, list), "Expected a list when n is integer"
    assert result == [{"i": 0}, {"i": 1}, {"i": 2}]


def test_query_handles_keyboardinterrupt_then_recovers_round_029(monkeypatch, capsys):
    instance = _make_instance()

    # Create an iterator that first raises KeyboardInterrupt, then returns a dict
    seq = iter(["raise", {"ok": True}])

    def fake_query(self, history, action_prompt):
        v = next(seq)
        if v == "raise":
            raise KeyboardInterrupt
        return v

    monkeypatch.setattr(HumanModel, "_query", fake_query)

    # Call and capture stdout for the printed message
    result = instance.query(history=None)

    captured = capsys.readouterr()
    # The code prints the caret message on KeyboardInterrupt
    assert "^C (exit with ^D)" in captured.out
    # After recovery, the function should return the dict from the second call
    assert result == {"ok": True}


def test_query_handles_eoferror_returns_exit_message_round_029(monkeypatch, capsys):
    instance = _make_instance()

    def fake_query_raise_eof(self, history, action_prompt):
        raise EOFError

    monkeypatch.setattr(HumanModel, "_query", fake_query_raise_eof)

    result = instance.query(history=None)
    captured = capsys.readouterr()

    # The code prints a goodbye message (with a leading newline in the print call)
    assert "Goodbye!" in captured.out
    # When EOFError occurs, the code appends {"message": "exit"} and returns it
    assert result == {"message": "exit"}
