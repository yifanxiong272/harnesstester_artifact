# file: aider/gui.py:328-349
# asked: {"lines": [328, 329, 330, 331, 334, 335, 336, 337, 338, 339, 340, 342, 344, 345, 346, 347, 348, 349], "branches": [[344, 0], [344, 345]]}
# gained: {"lines": [328, 329, 330, 331, 334, 335, 336, 337, 338, 339, 340, 342, 344, 345, 346, 347, 348, 349], "branches": [[344, 0], [344, 345]]}

import pytest
from types import SimpleNamespace

from aider.gui import GUI


class FakeState:
    def __init__(self, keys=None, preset_input_history=None):
        # keys is a set-like container
        self.keys = set(keys or [])
        self.inits = {}
        # allow preset input_history if desired
        if preset_input_history is not None:
            self.input_history = list(preset_input_history)

    def init(self, name, value=None):
        # store what was initialized and also set as attribute for accessibility
        self.inits[name] = value
        setattr(self, name, value)


class FakeIO:
    def __init__(self, history_iterable, on_get_called=None):
        self._history = list(history_iterable)
        self._on_get_called = on_get_called

    def get_input_history(self):
        if self._on_get_called:
            self._on_get_called()
        # return an iterator to mirror real behavior
        return iter(self._history)

    def add_to_input_history(self, v):
        # not used in these tests, but present for completeness
        self._history.append(v)


class FakeCoder:
    def __init__(self, last_aider_commit_hash, inchat_files, input_history_iterable, on_get_called=None):
        self.last_aider_commit_hash = last_aider_commit_hash
        self._inchat_files = list(inchat_files)
        self.io = FakeIO(input_history_iterable, on_get_called=on_get_called)

    def get_inchat_relative_files(self):
        return list(self._inchat_files)


def make_self(announce_ret="ANNOUNCE", coder=None, state=None):
    # create a minimal object that can be used as 'self' for GUI.initialize_state
    s = SimpleNamespace()
    s.announce = lambda: announce_ret
    s.coder = coder or FakeCoder("hash0", [], [], on_get_called=None)
    s.state = state or FakeState()
    return s


def test_initialize_state_adds_input_history_and_sets_inits():
    # coder has duplicated entries in history to exercise deduplication logic
    history = ["first", "second", "first", "third", "second"]
    coder = FakeCoder("commit-hash-1", ["file1.py", "file2.txt"], history)
    state = FakeState(keys=set())  # no 'input_history' in keys, so branch should run

    self = make_self(announce_ret="WELCOME", coder=coder, state=state)

    # Call the GUI.initialize_state unbound function with our fake self
    GUI.initialize_state(self)

    # Verify state.init was called for the expected keys and values
    # messages: first entry content should be announce() result
    assert "messages" in state.inits
    msgs = state.inits["messages"]
    assert isinstance(msgs, list) and msgs[0]["role"] == "info"
    assert msgs[0]["content"] == "WELCOME"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "How can I help you?"

    # last_aider_commit_hash should be set from coder
    assert state.inits["last_aider_commit_hash"] == "commit-hash-1"

    # last_undone_commit_hash was initialized without a value -> should be None
    assert "last_undone_commit_hash" in state.inits
    assert state.inits["last_undone_commit_hash"] is None

    # recent_msgs_num and web_content_num should be set to 0
    assert state.inits["recent_msgs_num"] == 0
    assert state.inits["web_content_num"] == 0

    # prompt and scraper should be initialized (to None)
    assert "prompt" in state.inits
    assert state.inits["prompt"] is None
    assert "scraper" in state.inits
    assert state.inits["scraper"] is None

    # initial_inchat_files should reflect coder.get_inchat_relative_files()
    assert state.inits["initial_inchat_files"] == ["file1.py", "file2.txt"]

    # The input_history branch should have run: state.input_history should be deduped keeping order
    assert hasattr(state, "input_history")
    assert state.input_history == ["first", "second", "third"]

    # 'input_history' should have been added to state.keys
    assert "input_history" in state.keys


def test_initialize_state_skips_input_history_when_present():
    # Here we ensure that when 'input_history' is already in state.keys,
    # coder.io.get_input_history is NOT called.
    called = {"flag": False}

    def mark_called():
        called["flag"] = True

    coder = FakeCoder("commit-2", ["f.py"], ["a", "b"], on_get_called=mark_called)
    # preset an existing input_history and include it in keys
    state = FakeState(keys={"input_history"}, preset_input_history=["existing"])

    self = make_self(announce_ret="HI", coder=coder, state=state)

    # Call initialize_state; since 'input_history' in state.keys, get_input_history should not be called
    GUI.initialize_state(self)

    # Ensure get_input_history was NOT called
    assert called["flag"] is False

    # Ensure existing input_history was left alone (not overwritten)
    assert state.input_history == ["existing"]

    # Ensure 'input_history' remains in keys
    assert "input_history" in state.keys

    # Other inits should still have been set
    assert state.inits["last_aider_commit_hash"] == "commit-2"
    assert state.inits["initial_inchat_files"] == ["f.py"]
