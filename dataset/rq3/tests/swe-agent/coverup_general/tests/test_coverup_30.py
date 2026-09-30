# file: sweagent/agent/models.py:406-421
# asked: {"lines": [408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421], "branches": [[410, 411], [410, 419], [419, 420], [419, 421]]}
# gained: {"lines": [408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421], "branches": [[410, 411], [410, 419], [419, 420], [419, 421]]}

import pytest

from sweagent.agent.models import HumanModel, HumanModelConfig
from sweagent.tools.tools import ToolConfig


def make_sequenced_query_fn(sequence):
    """
    Returns a function(history, action_prompt) that on each call returns or raises
    the next item from sequence. If the item is an Exception instance, it will be raised.
    After the sequence is exhausted, the last item will be returned/raised repeatedly.
    """
    seq = list(sequence)
    if not seq:
        raise ValueError("sequence must have at least one element")
    index = {"i": 0}

    def _fn(history, action_prompt):
        i = index["i"]
        if i >= len(seq):
            item = seq[-1]
        else:
            item = seq[i]
            index["i"] = i + 1
        if isinstance(item, BaseException):
            raise item
        return item

    return _fn


def make_model(monkeypatch, config=None, tools=None):
    # prevent file/IO interactions during init
    monkeypatch.setattr(HumanModel, "_load_readline_history", lambda self: None)
    cfg = config or HumanModelConfig()
    tools_cfg = tools or ToolConfig()
    return HumanModel(cfg, tools_cfg)


def test_query_returns_single_result(monkeypatch):
    m = make_model(monkeypatch)
    m._query = make_sequenced_query_fn([{"message": "ok"}])
    result = m.query(history=[])
    assert isinstance(result, dict)
    assert result == {"message": "ok"}


def test_query_with_n_returns_list_of_results(monkeypatch):
    m = make_model(monkeypatch)
    seq = [{"message": f"v{i}"} for i in range(3)]
    m._query = make_sequenced_query_fn(seq)
    result = m.query(history=[], n=3)
    assert isinstance(result, list)
    assert len(result) == 3
    assert result == seq


def test_query_handles_keyboard_interrupt_and_recovers(monkeypatch, capsys):
    m = make_model(monkeypatch)
    seq = [KeyboardInterrupt(), {"message": "recovered"}]
    m._query = make_sequenced_query_fn(seq)
    result = m.query(history=[], action_prompt="> ")
    captured = capsys.readouterr()
    assert "^C (exit with ^D)" in captured.out
    assert result == {"message": "recovered"}


def test_query_handles_eoferror_and_returns_exit_message(monkeypatch, capsys):
    m = make_model(monkeypatch)
    m._query = make_sequenced_query_fn([EOFError()])
    result = m.query(history=[])
    captured = capsys.readouterr()
    assert "Goodbye!" in captured.out
    assert result == {"message": "exit"}


def test_query_with_n_mixed_normal_and_eof(monkeypatch, capsys):
    m = make_model(monkeypatch)
    seq = [{"message": "first"}, EOFError()]
    m._query = make_sequenced_query_fn(seq)
    result = m.query(history=[], n=2)
    captured = capsys.readouterr()
    assert isinstance(result, list)
    assert result[0] == {"message": "first"}
    assert result[1] == {"message": "exit"}
    assert "Goodbye!" in captured.out
