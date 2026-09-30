import types
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from aider import gui as gui_mod
from aider.gui import GUI


def make_st_stub(record):
    """Create a simple stub for the streamlit (st) interface used by show_edit_info.

    record is a dict where call information will be appended.
    """

    class DummyCtx:
        def __init__(self, tag, kind):
            self.tag = tag
            self.kind = kind

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def expander(label):
        record.setdefault("expander_labels", []).append(label)
        return DummyCtx(label, "expander")

    def container(*args, **kwargs):
        # record the border kwarg and any positional args
        record.setdefault("container_calls", []).append({
            "args": args,
            "kwargs": kwargs,
        })
        return DummyCtx(kwargs.get("border"), "container")

    def code(value, language=None):
        record.setdefault("code_calls", []).append((value, language))

    def write(value):
        record.setdefault("write_calls", []).append(value)

    return SimpleNamespace(expander=expander, container=container, code=code, write=write)


def call_show_edit_info_with_stub(self_obj, edit, st_record):
    """Helper to patch gui_mod.st with a controllable stub and call show_edit_info.

    Returns the st_record for assertions.
    """
    stub = make_st_stub(st_record)
    # Patch the st object on the module under test
    original_st = getattr(gui_mod, "st", None)
    try:
        setattr(gui_mod, "st", stub)
        # Call the unbound function to avoid GUI.__init__ side effects
        GUI.show_edit_info(self_obj, edit)
    finally:
        # restore to avoid test interaction
        setattr(gui_mod, "st", original_st)
    return st_record


def test_show_edit_info_no_commit_no_fnames_round_025():
    """When neither commit_hash nor fnames are provided, function should return early.

    No streamlit context managers should be invoked and add_undo should not be called.
    """
    st_record = {}
    dummy_self = SimpleNamespace(coder=SimpleNamespace(last_aider_commit_hash=None), add_undo=Mock())

    # call with an edit that has no commit_hash and no fnames
    edit = {"commit_message": "ignored", "diff": None}

    call_show_edit_info_with_stub(dummy_self, edit, st_record)

    assert st_record == {}, "No st calls should have been recorded when nothing to show"
    dummy_self.add_undo.assert_not_called()


def test_show_edit_info_commit_and_fnames_and_diff_with_undo_round_025():
    """Full path: commit present (equals last_aider_commit_hash), fnames present and unsorted, diff present.

    Expect: expander called with combined res (commit line + applied edits), st.code called with diff and language='diff', and add_undo called once with the commit hash.
    """
    st_record = {}
    commit_hash = "abc123"
    commit_message = "Fix bug"
    # intentionally unsorted list to exercise sorting
    fnames = ["z.py", "a.py"]
    diff = "-old\n+new"

    dummy_self = SimpleNamespace(coder=SimpleNamespace(last_aider_commit_hash=commit_hash), add_undo=Mock())

    edit = {"commit_hash": commit_hash, "commit_message": commit_message, "diff": diff, "fnames": fnames}

    call_show_edit_info_with_stub(dummy_self, edit, st_record)

    # Verify expander was invoked with the expected composed message
    # The function sorts fnames and wraps each in backticks
    sorted_fnames = sorted(fnames)
    backticked = [f"`{n}`" for n in sorted_fnames]
    expected_fnames_part = ", ".join(backticked)
    expected_res = f"Commit `{commit_hash}`: {commit_message}  \n" + f"Applied edits to {expected_fnames_part}."

    assert st_record.get("expander_labels") == [expected_res]
    assert st_record.get("code_calls") == [(diff, "diff")]
    dummy_self.add_undo.assert_called_once_with(commit_hash)


def test_show_edit_info_commit_no_fnames_no_diff_show_undo_true_round_025():
    """Commit present and equals last_aider_commit_hash, no fnames, no diff -> container + write + add_undo called.
    """
    st_record = {}
    commit_hash = "xyz"
    commit_message = "Add feature"

    dummy_self = SimpleNamespace(coder=SimpleNamespace(last_aider_commit_hash=commit_hash), add_undo=Mock())

    edit = {"commit_hash": commit_hash, "commit_message": commit_message, "diff": None, "fnames": None}

    call_show_edit_info_with_stub(dummy_self, edit, st_record)

    # Expect container called once with border=True and write called with the composed res
    sorted_fnames_part = ""  # none
    expected_res = f"Commit `{commit_hash}`: {commit_message}  \n"

    container_calls = st_record.get("container_calls")
    assert container_calls and container_calls[0]["kwargs"].get("border") is True
    assert st_record.get("write_calls") == [expected_res]
    dummy_self.add_undo.assert_called_once_with(commit_hash)


def test_show_edit_info_fnames_without_commit_round_025():
    """No commit_hash but fnames present -> should not return early, should write applied edits, and not call add_undo.
    """
    st_record = {}
    fnames = ["one.txt"]
    dummy_self = SimpleNamespace(coder=SimpleNamespace(last_aider_commit_hash=None), add_undo=Mock())

    edit = {"commit_hash": None, "commit_message": None, "diff": None, "fnames": fnames}

    call_show_edit_info_with_stub(dummy_self, edit, st_record)

    # Expect write called with applied edits string and no add_undo
    expected_res = "Applied edits to `one.txt`."
    assert st_record.get("write_calls") == [expected_res]
    dummy_self.add_undo.assert_not_called()
