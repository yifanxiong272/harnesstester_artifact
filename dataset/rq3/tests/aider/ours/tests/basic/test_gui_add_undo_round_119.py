import types
import pytest

import aider.gui as gui_module


class PrevEmpty:
    def __init__(self):
        self.empty_called = False

    def empty(self):
        self.empty_called = True


class NewEmpty:
    def __init__(self):
        self.entered = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_st_empty_factory(new_empty_instance):
    # Return a callable that always returns the provided new_empty_instance
    def empty():
        return new_empty_instance

    return empty


def test_add_undo_with_existing_last_empty_and_button_false_round_119(monkeypatch):
    """
    - previous last_undo_empty exists and its empty() should be called
    - st.empty() returns a context manager (NewEmpty)
    - state.last_undone_commit_hash != commit_hash so the with-block is entered
    - button returns False so do_undo should NOT be called
    """
    prev = PrevEmpty()
    new = NewEmpty()

    # Patch st.empty to deterministically return our NewEmpty instance
    monkeypatch.setattr(gui_module, "st", types.SimpleNamespace(empty=make_st_empty_factory(new)))

    # Prepare a fake self object with required attributes and methods
    self_obj = types.SimpleNamespace()
    self_obj.last_undo_empty = prev
    self_obj.state = types.SimpleNamespace(last_undone_commit_hash="other_commit")

    # Track whether do_undo was called
    self_obj.did_undo = None

    def do_undo_impl(commit_hash):
        # mutates state so the test can assert
        self_obj.did_undo = commit_hash

    # button returns False to avoid undo
    def button_impl(*args, **kwargs):
        # intentionally return False
        return False

    self_obj.button = button_impl
    self_obj.do_undo = do_undo_impl

    # Call the unbound method with our fake self
    gui_module.GUI.add_undo(self_obj, "commit-123")

    # Assertions:
    # previous empty() called
    assert prev.empty_called is True
    # last_undo_empty replaced with our NewEmpty instance
    assert self_obj.last_undo_empty is new
    # because undone was False, we entered the with-block so __enter__ ran
    assert new.entered is True
    # button returned False so do_undo should not have been called
    assert self_obj.did_undo is None


def test_add_undo_with_no_prev_and_already_undone_round_119(monkeypatch):
    """
    - no previous last_undo_empty (None) so no empty() call
    - st.empty() returns a context manager but the with-block should be skipped
      because state.last_undone_commit_hash == commit_hash
    - button and do_undo should NOT be called
    """
    new = NewEmpty()
    monkeypatch.setattr(gui_module, "st", types.SimpleNamespace(empty=make_st_empty_factory(new)))

    # fake self with no previous last_undo_empty
    self_obj = types.SimpleNamespace()
    self_obj.last_undo_empty = None
    # set last_undone_commit_hash equal to the commit we pass => undone True
    self_obj.state = types.SimpleNamespace(last_undone_commit_hash="commit-abc")

    # trackers
    called = {"button": False, "do_undo": False}

    def button_impl(*args, **kwargs):
        called["button"] = True
        return True

    def do_undo_impl(commit_hash):
        called["do_undo"] = True

    self_obj.button = button_impl
    self_obj.do_undo = do_undo_impl

    gui_module.GUI.add_undo(self_obj, "commit-abc")

    # previous was None so nothing to call on it
    # last_undo_empty replaced with new instance
    assert self_obj.last_undo_empty is new
    # since undone == True, the with-block should not execute so __enter__ not called
    assert new.entered is False
    # button and do_undo must not have been invoked
    assert called["button"] is False
    assert called["do_undo"] is False


def test_add_undo_triggers_do_undo_when_button_true_round_119(monkeypatch):
    """
    - previous last_undo_empty falsy
    - st.empty returns NewEmpty
    - state.last_undone_commit_hash != commit_hash so with-block runs
    - button returns True and do_undo should be called with the commit hash
    """
    new = NewEmpty()
    monkeypatch.setattr(gui_module, "st", types.SimpleNamespace(empty=make_st_empty_factory(new)))

    self_obj = types.SimpleNamespace()
    self_obj.last_undo_empty = None
    self_obj.state = types.SimpleNamespace(last_undone_commit_hash="some-other")

    # trackers
    record = {"button_called": False, "did_undo_with": None}

    def button_impl(*args, **kwargs):
        record["button_called"] = True
        return True

    def do_undo_impl(commit_hash):
        record["did_undo_with"] = commit_hash

    self_obj.button = button_impl
    self_obj.do_undo = do_undo_impl

    gui_module.GUI.add_undo(self_obj, "commit-XYZ")

    # With-block should have been entered
    assert new.entered is True
    # button should have been called and returned True
    assert record["button_called"] is True
    # do_undo should have been called with the commit hash
    assert record["did_undo_with"] == "commit-XYZ"
