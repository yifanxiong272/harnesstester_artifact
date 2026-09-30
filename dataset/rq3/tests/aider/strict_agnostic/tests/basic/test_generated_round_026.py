import sys
import types
from types import SimpleNamespace
import importlib

# Provide a lightweight fake streamlit module so importing aider.gui doesn't require the real streamlit package.
fake_st = types.ModuleType("streamlit")

class _DummyCM:
    def __init__(self, calls, kind, title_or_kwargs=None):
        self.calls = calls
        self.kind = kind
        self.title_or_kwargs = title_or_kwargs
    def __enter__(self):
        # return an object that could be used inside the context if needed
        return self
    def __exit__(self, exc_type, exc, tb):
        return False

# default no-op behaviors; tests will override these per-case
_calls_global = []

def _default_expander(title):
    _calls_global.append(("expander_entered", title))
    return _DummyCM(_calls_global, "expander", title)

def _default_container(*args, **kwargs):
    _calls_global.append(("container_entered", args, kwargs))
    return _DummyCM(_calls_global, "container", kwargs)

def _default_code(diff, language=None):
    _calls_global.append(("code", diff, language))

def _default_write(msg):
    _calls_global.append(("write", msg))

fake_st.expander = _default_expander
fake_st.container = _default_container
fake_st.code = _default_code
fake_st.write = _default_write
# Repair: the real module uses @st.cache_resource at import time; provide a no-op decorator
fake_st.cache_resource = lambda f: f

# insert fake streamlit into sys.modules before importing the target module
sys.modules.setdefault("streamlit", fake_st)

# Now import the module under test
import aider.gui as gui_module

# Grab the unbound function so we can call it with a minimal fake "self"
show_edit_info = gui_module.GUI.show_edit_info

import pytest

# Helper to create a fake "self" object with a coder and an add_undo recording
class FakeSelf:
    def __init__(self, last_hash=None):
        self.coder = SimpleNamespace(last_aider_commit_hash=last_hash)
        self.added_undos = []
    def add_undo(self, commit_hash):
        self.added_undos.append(commit_hash)


def _install_st_mocks(calls):
    # Replace the streamlit functions on the imported module with mocks that record into `calls`.
    def expander(title):
        calls.append(("expander_entered", title))
        return _DummyCM(calls, "expander", title)
    def container(*args, **kwargs):
        calls.append(("container_entered", args, kwargs))
        return _DummyCM(calls, "container", kwargs)
    def code(diff, language=None):
        calls.append(("code", diff, language))
    def write(msg):
        calls.append(("write", msg))
    gui_module.st.expander = expander
    gui_module.st.container = container
    gui_module.st.code = code
    gui_module.st.write = write


def test_show_edit_info_commit_with_diff_and_matching_hash_round_026():
    """
    - commit_hash present and equals last_aider_commit_hash
    - diff present
    Expect: uses st.expander, calls st.code with the diff and language='diff', and add_undo called once with the commit hash.
    """
    calls = []
    _install_st_mocks(calls)

    fake = FakeSelf(last_hash="abc123")
    edit = {"commit_hash": "abc123", "commit_message": "Made changes", "diff": "-old\n+new", "fnames": None}

    # Call the unbound method with our fake self
    result = show_edit_info(fake, edit)

    # The function should not return any value (implicitly None)
    assert result is None

    # Confirm expander path was taken and code() was called with the diff and language
    assert any(c[0] == "expander_entered" for c in calls), f"expander not used, calls: {calls}"
    assert any(c[0] == "code" and c[1] == "-old\n+new" and c[2] == "diff" for c in calls), f"code not called correctly, calls: {calls}"

    # add_undo should have been called exactly once with the commit hash
    assert fake.added_undos == ["abc123"]


def test_show_edit_info_commit_with_no_matching_hash_and_no_diff_round_026():
    """
    - commit_hash present but does NOT equal last_aider_commit_hash
    - diff is None
    Expect: uses st.container and st.write to display the assembled message; add_undo NOT called.
    """
    calls = []
    _install_st_mocks(calls)

    fake = FakeSelf(last_hash="otherhash")
    edit = {"commit_hash": "abc123", "commit_message": "Message here", "diff": None, "fnames": None}

    result = show_edit_info(fake, edit)
    assert result is None

    # Confirm container path used and write called with the assembled message
    assert any(c[0] == "container_entered" for c in calls), f"container not used, calls: {calls}"
    assert any(c[0] == "write" and "Commit `abc123`" in c[1] for c in calls), f"write not called with expected message, calls: {calls}"

    # add_undo should NOT have been called
    assert fake.added_undos == []


def test_show_edit_info_only_fnames_sorted_and_container_round_026():
    """
    - no commit_hash, fnames provided unsorted
    - diff is None
    Expect: fnames get sorted, formatted with backticks and joined, displayed via st.container->st.write, add_undo NOT called.
    """
    calls = []
    _install_st_mocks(calls)

    fake = FakeSelf(last_hash=None)
    # unordered list; function should sort them alphabetically
    edit = {"commit_hash": None, "commit_message": None, "diff": None, "fnames": ["z.txt", "a.txt", "m.txt"]}

    result = show_edit_info(fake, edit)
    assert result is None

    # Ensure the container path was used and that the written message contains sorted, formatted filenames
    assert any(c[0] == "container_entered" for c in calls), f"container not used: {calls}"
    written = [c[1] for c in calls if c[0] == "write"]
    assert written, f"no write calls recorded: {calls}"
    out = written[-1]
    # Check that filenames are sorted and each is backticked and comma-separated in the output
    assert "`a.txt`" in out and "`m.txt`" in out and "`z.txt`" in out
    # a.txt should appear before m.txt and z.txt
    assert out.index("`a.txt`") < out.index("`m.txt`") < out.index("`z.txt`")

    # add_undo should not be called because there is no commit hash
    assert fake.added_undos == []


def test_show_edit_info_returns_early_when_no_commit_and_no_fnames_round_026():
    """
    - neither commit_hash nor fnames provided
    Expect: function returns early and does not call any st.* display functions nor add_undo.
    """
    calls = []
    _install_st_mocks(calls)

    fake = FakeSelf(last_hash=None)
    edit = {"commit_hash": None, "commit_message": None, "diff": "some diff", "fnames": None}

    result = show_edit_info(fake, edit)
    # When both commit_hash and fnames are falsy the function returns immediately (None)
    assert result is None

    # No UI calls should have been made
    assert calls == [], f"expected no streamlit calls, got: {calls}"
    assert fake.added_undos == []
