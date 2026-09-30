# file: aider/gui.py:138-147
# asked: {"lines": [138, 139, 140, 142, 143, 144, 145, 146, 147], "branches": [[139, 140], [139, 142], [144, 0], [144, 145], [146, 0], [146, 147]]}
# gained: {"lines": [138, 139, 140, 142, 143, 144, 145, 146, 147], "branches": [[139, 140], [139, 142], [144, 0], [144, 145], [146, 147]]}

import types
import importlib
import pytest

import aider.gui as gui_module


class FakeEmpty:
    def __init__(self):
        self.emptied = False
        self.entered = False
        self.exited = False

    def empty(self):
        self.emptied = True

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exited = True
        return False


class FakeSt:
    def __init__(self):
        self.created = []

    def empty(self):
        fe = FakeEmpty()
        self.created.append(fe)
        return fe


class DummyState:
    def __init__(self, last_undone_commit_hash=None):
        self.last_undone_commit_hash = last_undone_commit_hash


def make_dummy(button_return=False):
    """
    Create a dummy 'self' object that has the attributes/methods used by GUI.add_undo.
    """
    dummy = types.SimpleNamespace()
    dummy.last_undo_empty = None
    dummy.state = DummyState()
    # button will record calls
    calls = {"called": 0, "last_args": None}

    def button(text, key=None):
        calls["called"] += 1
        calls["last_args"] = (text, key)
        return button_return

    dummy.button = button

    # do_undo will record calls
    undone = {"called": 0, "last_commit": None}

    def do_undo(commit_hash):
        undone["called"] += 1
        undone["last_commit"] = commit_hash

    dummy.do_undo = do_undo

    # attach trackers so tests can assert
    dummy._tracker = {"button": calls, "do_undo": undone}
    return dummy


def test_add_undo_calls_do_undo_and_clears_previous(monkeypatch):
    """
    Test the path where last_undo_empty exists, undone is False, and the button returns True,
    so do_undo should be called and previous.empty() should be invoked. Also last_undo_empty
    should be replaced with the new object returned by st.empty().
    """
    fake_st = FakeSt()
    monkeypatch.setattr(gui_module, "st", fake_st)

    # create dummy with button returning True
    dummy = make_dummy(button_return=True)

    # Set an existing last_undo_empty so its .empty() is called
    previous = FakeEmpty()
    dummy.last_undo_empty = previous

    # ensure state indicates not already undone
    dummy.state.last_undone_commit_hash = "different"

    commit_hash = "abc123"

    # Call the unbound method with our dummy as self
    gui_module.GUI.add_undo(dummy, commit_hash)

    # Assertions:
    # previous empty() should have been called
    assert previous.emptied is True, "previous.last_undo_empty.empty() was not called"

    # a new empty placeholder should have been created and assigned
    assert isinstance(dummy.last_undo_empty, FakeEmpty)
    # it should be the last created in fake_st
    assert fake_st.created[-1] is dummy.last_undo_empty

    # button should have been called exactly once with expected text and key
    expected_text = f"Undo commit `{commit_hash}`"
    expected_key = f"undo_{commit_hash}"
    assert dummy._tracker["button"]["called"] == 1
    assert dummy._tracker["button"]["last_args"] == (expected_text, expected_key)

    # do_undo should have been called with commit_hash
    assert dummy._tracker["do_undo"]["called"] == 1
    assert dummy._tracker["do_undo"]["last_commit"] == commit_hash


def test_add_undo_skips_when_already_undone_and_handles_none_previous(monkeypatch):
    """
    Test the path where last_undo_empty is None initially and the commit is already marked
    as undone in state. In this case the with-block should be skipped (no button/do_undo calls),
    but last_undo_empty should still be set to the new placeholder returned by st.empty().
    """
    fake_st = FakeSt()
    monkeypatch.setattr(gui_module, "st", fake_st)

    # create dummy with button returning True (should not be used because undone=True)
    dummy = make_dummy(button_return=True)

    # start with last_undo_empty = None
    dummy.last_undo_empty = None

    # mark the commit as already undone
    commit_hash = "already_undone"
    dummy.state.last_undone_commit_hash = commit_hash

    gui_module.GUI.add_undo(dummy, commit_hash)

    # Since previous was None, nothing to empty, but last_undo_empty should now be set
    assert isinstance(dummy.last_undo_empty, FakeEmpty)
    assert fake_st.created[-1] is dummy.last_undo_empty

    # button should NOT have been called because undone == True
    assert dummy._tracker["button"]["called"] == 0

    # do_undo should NOT have been called
    assert dummy._tracker["do_undo"]["called"] == 0
