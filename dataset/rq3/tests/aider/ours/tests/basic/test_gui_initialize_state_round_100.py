import types

import pytest

# Import the GUI class from the module under test.
# We avoid calling GUI.__init__ to prevent side effects; tests will bind required attributes manually.
from aider.gui import GUI


class FakeState:
    """Minimal fake state implementing the interface used by initialize_state.

    - .init(key, val=None) stores the value and sets attribute on self
    - .storage lets tests inspect what was stored
    - .keys is a set used for membership checks and .add
    """

    def __init__(self, initial_keys=None, prefilled=None):
        self.storage = {} if prefilled is None else dict(prefilled)
        self.keys = set(initial_keys or [])
        # ensure any prefilled storage appears as attributes
        for k, v in self.storage.items():
            setattr(self, k, v)

    def init(self, key, val=None):
        # mirrors the probable behavior in the real State: set attribute and record storage
        self.storage[key] = val
        setattr(self, key, val)


class FakeIO:
    def __init__(self, history):
        # history: iterable of input history items (can contain duplicates)
        self._history = list(history)
        self.called = False

    def get_input_history(self):
        # mark called for assertions and return an iterator
        self.called = True
        return iter(self._history)


class FakeCoder:
    def __init__(self, last_hash, inchat_files, io):
        self.last_aider_commit_hash = last_hash
        self._inchat_files = list(inchat_files)
        self.io = io

    def get_inchat_relative_files(self):
        return list(self._inchat_files)


def make_gui_instance(announce_value, state_obj, coder_obj):
    # Create a GUI instance without running __init__ to avoid unrelated side effects.
    gui = object.__new__(GUI)
    # bind attributes used by initialize_state
    gui.state = state_obj
    gui.coder = coder_obj
    # announce is an instance method; set as a simple function attribute
    gui.announce = types.MethodType(lambda self: announce_value, gui)
    return gui


def test_initialize_state_with_input_history_present_round_100():
    """When 'input_history' is already present in state.keys, the code must not call coder.io.get_input_history
    and should not overwrite the existing input_history attribute.
    """
    # Prepare a fake state that already has 'input_history' and a pre-existing value.
    pre_existing_input_history = ["existing-message"]
    prefilled = {"input_history": pre_existing_input_history}
    state = FakeState(initial_keys={"input_history"}, prefilled=prefilled)

    # Prepare a FakeIO that would raise if used (we instead assert it's not called)
    io = FakeIO(history=["should-not-be-read"])
    coder = FakeCoder(last_hash="hash-123", inchat_files=["f1.py"], io=io)

    gui = make_gui_instance("ANNOUNCE_ME", state, coder)

    # Call the method under test
    gui.initialize_state()

    # Assertions: common initializations must have happened
    assert "messages" in state.storage
    messages = state.storage["messages"]
    # first message uses announce() result
    assert messages[0]["role"] == "info"
    assert messages[0]["content"] == "ANNOUNCE_ME"
    # second assistant prompt present
    assert messages[1] == {"role": "assistant", "content": "How can I help you?"}

    # last_aider_commit_hash stored from coder
    assert state.storage.get("last_aider_commit_hash") == "hash-123"
    # last_undone_commit_hash should be present as None (init called without value)
    assert "last_undone_commit_hash" in state.storage
    assert state.storage["last_undone_commit_hash"] is None

    # numeric inits
    assert state.storage.get("recent_msgs_num") == 0
    assert state.storage.get("web_content_num") == 0

    # initial_inchat_files should be populated from coder.get_inchat_relative_files
    assert state.storage.get("initial_inchat_files") == ["f1.py"]

    # Because 'input_history' was already present, coder.io.get_input_history must not have been invoked
    assert io.called is False

    # And existing input_history should be left untouched
    assert state.input_history == pre_existing_input_history
    # state.keys must still contain 'input_history'
    assert "input_history" in state.keys


def test_initialize_state_without_input_history_round_100():
    """When 'input_history' is not present, initialize_state must read coder.io.get_input_history(),
    deduplicate while preserving order, set state.input_history to the de-duplicated list, and add the key.
    """
    # Prepare a fake state without 'input_history'
    state = FakeState(initial_keys=set())

    # Provide io history with duplicates to verify dedup logic preserves first occurrences
    raw_history = ["a", "b", "a", "c", "b"]
    io = FakeIO(history=raw_history)
    coder = FakeCoder(last_hash="last-xyz", inchat_files=["alpha.txt", "beta.txt"], io=io)

    gui = make_gui_instance("WELCOME", state, coder)

    gui.initialize_state()

    # verify IO was called to populate history
    assert io.called is True

    # deduplicated expected order: a, b, c
    assert state.input_history == ["a", "b", "c"]
    # key must be added to keys set
    assert "input_history" in state.keys

    # check messages and other inits happened too
    assert state.storage["messages"][0]["content"] == "WELCOME"
    assert state.storage["last_aider_commit_hash"] == "last-xyz"
    assert state.storage["initial_inchat_files"] == ["alpha.txt", "beta.txt"]

    # Ensure numeric and None inits are present
    assert state.storage.get("recent_msgs_num") == 0
    assert state.storage.get("web_content_num") == 0
    assert "prompt" in state.storage and state.storage["prompt"] is None
    assert "scraper" in state.storage and state.storage["scraper"] is None
