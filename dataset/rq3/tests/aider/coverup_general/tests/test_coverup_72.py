# file: aider/gui.py:138-147
# asked: {"lines": [138, 139, 140, 142, 143, 144, 145, 146, 147], "branches": [[139, 140], [139, 142], [144, 0], [144, 145], [146, 0], [146, 147]]}
# gained: {"lines": [138, 139, 140, 142, 143, 144, 145, 146, 147], "branches": [[139, 140], [139, 142], [144, 0], [144, 145], [146, 0], [146, 147]]}

import types
import pytest

import importlib

import aider.gui as gui_mod
from aider.gui import GUI


class FakeNewEmpty:
    def __init__(self, name=None, tracker=None):
        self.name = name
        self.tracker = tracker

    def __enter__(self):
        # entering context — record if needed
        if self.tracker is not None:
            self.tracker.append(("enter", self.name))
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.tracker is not None:
            self.tracker.append(("exit", self.name))
        return False

    def empty(self):
        # allow being emptied later (shouldn't be called on the new one in our tests,
        # but implement to be safe)
        if self.tracker is not None:
            self.tracker.append(("empty_called_on_new", self.name))


class FakeOldEmpty:
    def __init__(self):
        self.empty_called = False

    def empty(self):
        self.empty_called = True


class FakeSt:
    def __init__(self):
        self.created = []
        self.tracker = []

    def empty(self):
        name = f"empty_{len(self.created)}"
        e = FakeNewEmpty(name=name, tracker=self.tracker)
        self.created.append(e)
        return e


def make_gui_without_init():
    # create GUI instance without running its __init__
    g = GUI.__new__(GUI)
    return g


def test_add_undo_no_prev_button_false(monkeypatch):
    """
    Case:
    - last_undo_empty is None
    - state.last_undone_commit_hash != commit_hash (undone False)
    - button returns False -> do_undo not called
    Expect:
    - st.empty() was called and assigned to last_undo_empty
    - button was called with expected args
    - do_undo not called
    """
    fake_st = FakeSt()
    monkeypatch.setattr(gui_mod, "st", fake_st)

    g = make_gui_without_init()
    g.last_undo_empty = None
    g.state = types.SimpleNamespace(last_undone_commit_hash="other")

    called = {}

    def fake_button(label, key=None):
        called['label'] = label
        called['key'] = key
        return False

    def fake_do_undo(ch):
        called['do_undo'] = ch

    g.button = fake_button
    g.do_undo = fake_do_undo

    commit_hash = "commit123"
    g.add_undo(commit_hash)

    # last_undo_empty should be set to a new empty from fake_st
    assert isinstance(g.last_undo_empty, FakeNewEmpty)
    assert fake_st.created, "st.empty() was not called"
    # button should have been called once with expected args
    assert called.get("label") == f"Undo commit `{commit_hash}`"
    assert called.get("key") == f"undo_{commit_hash}"
    # do_undo should not be called because button returned False
    assert "do_undo" not in called


def test_add_undo_prev_and_button_true(monkeypatch):
    """
    Case:
    - last_undo_empty is present => its .empty() should be called
    - state.last_undone_commit_hash != commit_hash (undone False)
    - button returns True -> do_undo should be called with commit_hash
    Expect:
    - old empty's empty() called
    - new empty assigned
    - do_undo called
    """
    fake_st = FakeSt()
    monkeypatch.setattr(gui_mod, "st", fake_st)

    g = make_gui_without_init()
    old = FakeOldEmpty()
    g.last_undo_empty = old
    g.state = types.SimpleNamespace(last_undone_commit_hash="different")

    recorded = {}

    def fake_button(label, key=None):
        # record and return True to trigger do_undo
        recorded['label'] = label
        recorded['key'] = key
        return True

    def fake_do_undo(ch):
        recorded['do_undo'] = ch

    g.button = fake_button
    g.do_undo = fake_do_undo

    commit_hash = "abcde"
    g.add_undo(commit_hash)

    # old.empty() must have been called
    assert old.empty_called is True
    # new empty assigned
    assert isinstance(g.last_undo_empty, FakeNewEmpty)
    # do_undo should have been called with commit_hash
    assert recorded.get("do_undo") == commit_hash
    # button called with expected args
    assert recorded.get("label") == f"Undo commit `{commit_hash}`"
    assert recorded.get("key") == f"undo_{commit_hash}"


def test_add_undo_prev_undone_true_skips_button(monkeypatch):
    """
    Case:
    - last_undo_empty present -> its .empty() called
    - state.last_undone_commit_hash == commit_hash (undone True)
    -> should not enter the with-block, so button and do_undo not called.
    """
    fake_st = FakeSt()
    monkeypatch.setattr(gui_mod, "st", fake_st)

    g = make_gui_without_init()
    old = FakeOldEmpty()
    g.last_undo_empty = old
    # set undone True
    commit_hash = "samehash"
    g.state = types.SimpleNamespace(last_undone_commit_hash=commit_hash)

    called = {}

    def fake_button(label, key=None):
        called['button_called'] = True
        return True

    def fake_do_undo(ch):
        called['do_undo'] = ch

    g.button = fake_button
    g.do_undo = fake_do_undo

    g.add_undo(commit_hash)

    # old.empty() must have been called
    assert old.empty_called is True
    # new empty assigned
    assert isinstance(g.last_undo_empty, FakeNewEmpty)
    # button and do_undo must NOT be called because undone==True
    assert 'button_called' not in called
    assert 'do_undo' not in called
