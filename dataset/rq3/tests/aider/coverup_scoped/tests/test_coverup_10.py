# file: aider/gui.py:104-136
# asked: {"lines": [104, 105, 106, 107, 108, 109, 110, 112, 113, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 127, 128, 129, 130, 131, 133, 134, 135, 136], "branches": [[109, 110], [109, 112], [112, 113], [112, 115], [117, 118], [117, 122], [119, 120], [119, 122], [122, 123], [122, 127], [127, 128], [127, 133], [130, 0], [130, 131], [135, 0], [135, 136]]}
# gained: {"lines": [104, 105, 106, 107, 108, 109, 110, 112, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 127, 128, 129, 130, 131, 133, 134, 135, 136], "branches": [[109, 110], [112, 115], [117, 118], [117, 122], [119, 120], [122, 123], [127, 128], [127, 133], [130, 131], [135, 0], [135, 136]]}

import types
from types import SimpleNamespace

import aider.gui as gui_mod
from aider.gui import GUI

import pytest


class FakeCtx:
    def __init__(self, parent, kind, info):
        self.parent = parent
        self.kind = kind
        self.info = info

    def __enter__(self):
        if self.kind == "expander":
            self.parent.expander_titles.append(self.info)
        elif self.kind == "container":
            self.parent.container_calls.append(self.info)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSt:
    def __init__(self):
        self.expander_titles = []
        self.container_calls = []
        self.codes = []
        self.writes = []

    def expander(self, title):
        return FakeCtx(self, "expander", title)

    def container(self, border=True):
        return FakeCtx(self, "container", border)

    def code(self, diff, language=None):
        self.codes.append((diff, language))

    def write(self, value):
        self.writes.append(value)

    # provide minimal chat_input to avoid GUI init interactions if ever called
    def chat_input(self, prompt):
        return None

    def rerun(self):
        return None


def make_gui_with_fake_st(monkeypatch, fake_st=None):
    if fake_st is None:
        fake_st = FakeSt()
    # Replace the st object inside the aider.gui module
    monkeypatch.setattr(gui_mod, "st", fake_st)
    # Create GUI instance without running __init__ to avoid side effects
    g = object.__new__(GUI)
    # Provide the minimal attributes show_edit_info expects
    g.coder = SimpleNamespace(last_aider_commit_hash=None)
    g.added_undos = []

    def add_undo(commit_hash):
        g.added_undos.append(commit_hash)

    g.add_undo = add_undo
    return g, fake_st


def test_show_edit_info_with_diff_and_undo(monkeypatch):
    g, fake_st = make_gui_with_fake_st(monkeypatch)

    g.coder.last_aider_commit_hash = "abc123"

    edit = {
        "commit_hash": "abc123",
        "commit_message": "Fix bugs",
        "diff": "--- a\n+++ b\n@@ -1 +1 @@\n-foo\n+bar\n",
        "fnames": ["b.py", "a.py"],
    }

    g.show_edit_info(edit)

    expected_fnames = "`a.py`, `b.py`"
    expected_res = f"Commit `abc123`: Fix bugs  \nApplied edits to {expected_fnames}."

    assert fake_st.expander_titles == [expected_res]
    assert fake_st.codes == [(edit["diff"], "diff")]
    assert g.added_undos == ["abc123"]


def test_show_edit_info_without_diff_triggers_container_and_undo(monkeypatch):
    g, fake_st = make_gui_with_fake_st(monkeypatch)

    g.coder.last_aider_commit_hash = "hash1"

    edit = {
        "commit_hash": "hash1",
        "commit_message": "Some change",
        "diff": None,
        "fnames": ["file.py"],
    }

    g.show_edit_info(edit)

    expected_res = "Commit `hash1`: Some change  \nApplied edits to `file.py`."

    assert fake_st.container_calls == [True]
    assert fake_st.writes == [expected_res]
    assert g.added_undos == ["hash1"]


def test_show_edit_info_fnames_only_no_undo(monkeypatch):
    g, fake_st = make_gui_with_fake_st(monkeypatch)

    g.coder.last_aider_commit_hash = "doesnotmatter"

    edit = {
        "commit_hash": None,
        "commit_message": None,
        "diff": None,
        "fnames": ["z.py"],
    }

    g.show_edit_info(edit)

    expected_res = "Applied edits to `z.py`."

    assert fake_st.container_calls == [True]
    assert fake_st.writes == [expected_res]
    assert g.added_undos == []
