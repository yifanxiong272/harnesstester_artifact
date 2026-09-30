# file: sweagent/run/compare_runs.py:69-104
# asked: {"lines": [69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104], "branches": [[85, 0], [85, 86], [88, 89], [88, 90], [90, 91], [90, 92], [92, 93], [92, 94], [94, 95], [94, 98], [96, 97], [96, 104], [98, 99], [98, 101], [102, 103], [102, 104]]}
# gained: {"lines": [69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104], "branches": [[85, 0], [85, 86], [88, 89], [88, 90], [90, 91], [90, 92], [92, 93], [92, 94], [94, 95], [94, 98], [96, 97], [96, 104], [98, 99], [98, 101], [102, 103], [102, 104]]}

import pytest
from pathlib import Path

from sweagent.run import compare_runs


def _make_getters(submitted_map, resolved_map):
    def get_submitted(path):
        # path may be Path; use its name to distinguish new vs old
        return submitted_map.get(Path(path).name, [])

    def get_resolved(path):
        return resolved_map.get(Path(path).name, [])

    return get_submitted, get_resolved


def test_new_entries_emojis(monkeypatch, capsys):
    # new: a (resolved), b (unresolved)
    submitted_map = {
        "new": ["a", "b"],
        "old": [],
    }
    resolved_map = {
        "new": ["a"],
        "old": [],
    }
    get_submitted, get_resolved = _make_getters(submitted_map, resolved_map)
    monkeypatch.setattr(compare_runs, "get_submitted", get_submitted)
    monkeypatch.setattr(compare_runs, "get_resolved", get_resolved)

    compare_runs.compare_pair(Path("new"), Path("old"))

    out = capsys.readouterr().out
    # header checks
    assert "Emoji legend:" in out
    assert "Total evaluated: new 2, old 0" in out
    # emoji lines
    assert "😀❓ a" in out
    assert "👾❓ b" in out


def test_resolved_now_but_not_before(monkeypatch, capsys):
    # c was evaluated before but not resolved before; now resolved -> 😀
    submitted_map = {"new": ["c"], "old": ["c"]}
    resolved_map = {"new": ["c"], "old": []}
    get_submitted, get_resolved = _make_getters(submitted_map, resolved_map)
    monkeypatch.setattr(compare_runs, "get_submitted", get_submitted)
    monkeypatch.setattr(compare_runs, "get_resolved", get_resolved)

    compare_runs.compare_pair(Path("new"), Path("old"))

    out = capsys.readouterr().out
    assert "😀 c" in out


def test_resolved_in_both_skipped_and_shown(monkeypatch, capsys):
    # d resolved in both; when show_same False it should be skipped;
    # when show_same True it should be printed as ✅
    submitted_map = {"new": ["d"], "old": ["d"]}
    resolved_map = {"new": ["d"], "old": ["d"]}
    get_submitted, get_resolved = _make_getters(submitted_map, resolved_map)
    monkeypatch.setattr(compare_runs, "get_submitted", get_submitted)
    monkeypatch.setattr(compare_runs, "get_resolved", get_resolved)

    # default (show_same=False) => should not print the ✅ line
    compare_runs.compare_pair(Path("new"), Path("old"))
    out1 = capsys.readouterr().out
    assert "✅ d" not in out1

    # with show_same True => it should print
    compare_runs.compare_pair(Path("new"), Path("old"), show_same=True)
    out2 = capsys.readouterr().out
    assert "✅ d" in out2


def test_resolved_before_now_unresolved(monkeypatch, capsys):
    # e was resolved before, but is unresolved now -> ❌
    submitted_map = {"new": ["e"], "old": ["e"]}
    resolved_map = {"new": [], "old": ["e"]}
    get_submitted, get_resolved = _make_getters(submitted_map, resolved_map)
    monkeypatch.setattr(compare_runs, "get_submitted", get_submitted)
    monkeypatch.setattr(compare_runs, "get_resolved", get_resolved)

    compare_runs.compare_pair(Path("new"), Path("old"))
    out = capsys.readouterr().out
    assert "❌ e" in out


def test_unresolved_in_both_skipped_and_shown(monkeypatch, capsys):
    # f evaluated in both, unresolved in both -> 👾 ; skipped unless show_same True
    submitted_map = {"new": ["f"], "old": ["f"]}
    resolved_map = {"new": [], "old": []}
    get_submitted, get_resolved = _make_getters(submitted_map, resolved_map)
    monkeypatch.setattr(compare_runs, "get_submitted", get_submitted)
    monkeypatch.setattr(compare_runs, "get_resolved", get_resolved)

    # default skip
    compare_runs.compare_pair(Path("new"), Path("old"))
    out1 = capsys.readouterr().out
    assert "👾 f" not in out1

    # show_same True -> should print
    compare_runs.compare_pair(Path("new"), Path("old"), show_same=True)
    out2 = capsys.readouterr().out
    assert "👾 f" in out2
