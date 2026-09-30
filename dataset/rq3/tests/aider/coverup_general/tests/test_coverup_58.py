# file: aider/gui.py:328-349
# asked: {"lines": [328, 329, 330, 331, 334, 335, 336, 337, 338, 339, 340, 342, 344, 345, 346, 347, 348, 349], "branches": [[344, 0], [344, 345]]}
# gained: {"lines": [328, 329, 330, 331, 334, 335, 336, 337, 338, 339, 340, 342, 344, 345, 346, 347, 348, 349], "branches": [[344, 0], [344, 345]]}

import types
import pytest

from aider.gui import GUI


class FakeState:
    def __init__(self, prekeys=None, pre_input_history=None):
        # store values set via init
        self.data = {}
        # keys set used by GUI.initialize_state membership checks
        self.keys = set(prekeys or ())
        # optional pre-existing input_history attribute (to check it's not overwritten)
        if pre_input_history is not None:
            self.input_history = pre_input_history

    def init(self, key, value=None):
        # mimic storing initialized keys/values
        self.data[key] = value


class DummyIO:
    def __init__(self, history_iterable):
        self._history = history_iterable
        self.called = False

    def get_input_history(self):
        # mark called for test verification and return iterator
        self.called = True
        for x in self._history:
            yield x


class DummyCoder:
    def __init__(self, last_hash, inchat_files, io):
        self.last_aider_commit_hash = last_hash
        self._inchat_files = inchat_files
        self.io = io

    def get_inchat_relative_files(self):
        return self._inchat_files


def make_gui_instance():
    # Create GUI instance without running any real __init__ (to avoid side-effects)
    gui = GUI.__new__(GUI)
    return gui


def test_initialize_state_adds_and_deduplicates_input_history(monkeypatch):
    gui = make_gui_instance()

    # Provide an announce method that the initialize_state uses
    gui.announce = lambda: "ANNOUNCE-MSG"

    # Fake coder with a history that contains duplicates to exercise dedup logic
    history = ["first", "second", "first", "third", "second"]
    dummy_io = DummyIO(history)
    coder = DummyCoder(last_hash="deadbeef", inchat_files=["a.py", "b.txt"], io=dummy_io)
    gui.coder = coder

    # Fake state that does not contain 'input_history' in its keys
    state = FakeState(prekeys=[])
    gui.state = state

    # Call the method under test
    gui.initialize_state()

    # Verify messages initialized correctly
    assert "messages" in state.data
    msgs = state.data["messages"]
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "info" and msgs[0]["content"] == "ANNOUNCE-MSG"
    assert msgs[1]["role"] == "assistant" and msgs[1]["content"] == "How can I help you?"

    # Verify last_aider_commit_hash initialized
    assert state.data.get("last_aider_commit_hash") == "deadbeef"

    # Verify initial_inchat_files set from coder
    assert state.data.get("initial_inchat_files") == ["a.py", "b.txt"]

    # Verify deduplicated input_history set on the state object in original order
    assert hasattr(state, "input_history")
    assert state.input_history == ["first", "second", "third"]

    # Verify 'input_history' key was added to state.keys
    assert "input_history" in state.keys

    # Ensure coder.io.get_input_history was actually called
    assert dummy_io.called is True


def test_initialize_state_skips_input_history_when_already_present(monkeypatch):
    gui = make_gui_instance()
    gui.announce = lambda: "NOOP"

    # Create a DummyIO that would raise if called to ensure branch isn't executed
    def raising_generator():
        raise AssertionError("get_input_history should not be called when input_history exists")

    class RaisingIO:
        def get_input_history(self):
            return raising_generator()

    dummy_io = RaisingIO()
    coder = DummyCoder(last_hash="hash2", inchat_files=[], io=dummy_io)
    gui.coder = coder

    # Fake state that already contains 'input_history' in keys and has a preexisting value
    pre_existing = ["already", "there"]
    state = FakeState(prekeys=["input_history"], pre_input_history=list(pre_existing))
    gui.state = state

    # Call initialize_state; should not try to get input history and should preserve existing value
    gui.initialize_state()

    # Verify that input_history attribute remains unchanged
    assert hasattr(state, "input_history")
    assert state.input_history == pre_existing

    # Verify 'input_history' still in keys and no duplicate addition occurred
    assert "input_history" in state.keys

    # Verify other inits still occurred (messages and last_aider_commit_hash)
    assert "messages" in state.data
    assert state.data.get("last_aider_commit_hash") == "hash2"
