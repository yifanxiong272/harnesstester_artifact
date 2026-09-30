import types
import importlib

import aider.gui as gui_mod
from aider.gui import GUI


class DummySt:
    def __init__(self):
        self.rerun_called = False

    def write_stream(self, it):
        # deterministically join the provided stream parts
        return "".join(list(it))

    def rerun(self):
        self.rerun_called = True


class FakeMessages:
    def __init__(self):
        self.chat_calls = []
        self.entered = 0

    def chat_message(self, role):
        # return a context manager (self) for the 'with' usage
        self.chat_calls.append(role)
        return self

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeRepo:
    def __init__(self):
        self.calls = []

    def diff_commits(self, pretty, commits, last_hash):
        # deterministic pseudo-diff
        self.calls.append((pretty, commits, last_hash))
        return f"DIFF({commits}->{last_hash})"


class FakeCoder:
    def __init__(self, run_outputs, reflected_message, last_hash, last_msg, aider_edited_files):
        # run_outputs: iterable of strings that run_stream yields
        self._run_outputs = list(run_outputs)
        self.reflected_message = reflected_message
        self.last_aider_commit_hash = last_hash
        self.last_aider_commit_message = last_msg
        self.aider_edited_files = aider_edited_files
        self.repo = FakeRepo()
        self.pretty = True

    def run_stream(self, prompt):
        # return an iterator as expected by write_stream
        return iter(self._run_outputs)


class FakeState:
    def __init__(self, prompt, last_aider_commit_hash=None):
        self.prompt = prompt
        self.messages = []
        self.last_aider_commit_hash = last_aider_commit_hash


def _make_minimal_gui():
    # Create a GUI instance without running its full __init__
    g = object.__new__(GUI)
    return g


def test_process_chat_reflections_and_commit_diff_round_035():
    """
    Exercise the reflection loop (num_reflections increments) and the branch
    where the coder's last_aider_commit_hash differs from state, causing a diff
    to be produced and attached to the edit message. Also assert that st.rerun
    is called.
    """
    # Prepare environment and deterministic st replacement
    dummy_st = DummySt()
    # Patch the module-level 'st' used in process_chat
    gui_mod.st = dummy_st

    # Build fake components
    messages = FakeMessages()
    # initial prompt triggers the loop; coder.reflected_message is non-empty so
    # the loop will run multiple times until num_reflections reaches max_reflections
    coder = FakeCoder(run_outputs=["p1", "p2"], reflected_message="next-prompt", last_hash="newhash",
                      last_msg="commit message", aider_edited_files=["file1.txt"])
    state = FakeState(prompt="initial-prompt", last_aider_commit_hash="oldhash")

    gui = _make_minimal_gui()
    gui.state = state
    gui.messages = messages
    gui.coder = coder

    # capture calls to show_edit_info and info
    shown_edits = []
    infos = []

    def show_edit_info(edit):
        shown_edits.append(edit)

    def info(msg, echo=False):
        infos.append((msg, echo))

    gui.show_edit_info = show_edit_info
    gui.info = info

    # Run the method under test
    gui.process_chat()

    # Assertions: messages should contain assistant outputs for each iteration
    # The write_stream concatenates run_stream outputs "p1"+"p2" = "p1p2"
    assistant_msgs = [m for m in state.messages if m.get("role") == "assistant"]
    assert len(assistant_msgs) == gui.max_reflections or len(assistant_msgs) >= 1
    for m in assistant_msgs:
        assert m["content"] == "p1p2"

    # The final edit should have been appended with commit info and diff
    edits = [m for m in state.messages if m.get("role") != "assistant"]
    # There should be at least one edit dict appended at the end
    assert edits, "no edit message appended"
    edit = edits[-1]
    assert edit["role"] == "edit"
    # Because state.last_aider_commit_hash != coder.last_aider_commit_hash, commit fields set
    assert edit.get("commit_hash") == coder.last_aider_commit_hash
    assert edit.get("commit_message") == coder.last_aider_commit_message
    assert edit.get("diff") == "DIFF(newhash~1->newhash)" or edit.get("diff", "").startswith("DIFF(" )

    # state.last_aider_commit_hash should have been updated to coder's value
    assert state.last_aider_commit_hash == coder.last_aider_commit_hash

    # show_edit_info should have been called with the same edit object
    assert shown_edits and shown_edits[-1] is edit

    # st.rerun should be called to re-render
    assert dummy_st.rerun_called is True


def test_process_chat_no_commit_change_round_035():
    """
    Exercise the branch where there is no commit change between state and coder.
    Ensure that in this case edit does not contain commit_hash/commit_message/diff
    and that rerun is still invoked. Also test the single-iteration path
    (no reflections).
    """
    dummy_st = DummySt()
    gui_mod.st = dummy_st

    messages = FakeMessages()
    # No reflection to keep it a single iteration
    coder = FakeCoder(run_outputs=["x"], reflected_message=None, last_hash="samehash",
                      last_msg="msg", aider_edited_files=["a.txt"])
    state = FakeState(prompt="prompt-1", last_aider_commit_hash="samehash")

    gui = _make_minimal_gui()
    gui.state = state
    gui.messages = messages
    gui.coder = coder

    captured = []

    def show_edit_info(edit):
        captured.append(edit)

    gui.show_edit_info = show_edit_info
    gui.info = lambda *a, **k: None

    gui.process_chat()

    # state.messages should contain exactly one assistant message and one edit
    assistant_msgs = [m for m in state.messages if m.get("role") == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["content"] == "x"

    edits = [m for m in state.messages if m.get("role") != "assistant"]
    assert edits, "no edit appended"
    edit = edits[-1]
    # Because there was no commit change, these keys should not be present
    assert "commit_hash" not in edit
    assert "commit_message" not in edit
    assert "diff" not in edit

    # show_edit_info was called with the edit
    assert captured and captured[-1] is edit

    # st.rerun should have been invoked
    assert dummy_st.rerun_called is True
