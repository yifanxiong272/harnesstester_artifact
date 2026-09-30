# file: aider/gui.py:498-521
# asked: {"lines": [498, 499, 502, 503, 505, 506, 508, 509, 510, 512, 513, 514, 515, 517, 519, 520, 521], "branches": [[501, 505], [501, 508], [519, 0], [519, 520]]}
# gained: {"lines": [498, 499, 502, 503, 505, 506, 508, 509, 510, 512, 513, 514, 515, 517, 519, 520, 521], "branches": [[501, 505], [501, 508], [519, 0], [519, 520]]}

import types
import builtins
import pytest

from aider import gui
from types import SimpleNamespace

def make_instance():
    # Create an instance without calling GUI.__init__
    inst = object.__new__(gui.GUI)
    return inst

class DummyEmpty:
    def __init__(self):
        self.called = False
    def empty(self):
        self.called = True

class DummyIO:
    def __init__(self, returns):
        # returns is a list of return values for successive calls
        self._returns = list(returns)
    def get_captured_lines(self):
        if self._returns:
            return self._returns.pop(0)
        return []

class DummyCommands:
    def __init__(self, io_obj, cmd_undo_fn):
        self.io = io_obj
        self._cmd_undo_fn = cmd_undo_fn
    def cmd_undo(self, arg):
        return self._cmd_undo_fn(arg)

def setup_basic_gui(commit_hash_state, commit_hash_coder, io_returns, cmd_undo_fn):
    inst = make_instance()

    # last_undo_empty with .empty()
    dummy_empty = DummyEmpty()
    inst.last_undo_empty = dummy_empty

    # state and coder SimpleNamespace objects
    inst.state = SimpleNamespace(last_aider_commit_hash=commit_hash_state,
                                 last_undone_commit_hash=None)
    coder = SimpleNamespace()
    coder.last_aider_commit_hash = commit_hash_coder

    io_obj = DummyIO(io_returns)
    commands = DummyCommands(io_obj, cmd_undo_fn)
    coder.commands = commands
    inst.coder = coder

    # Capture info calls
    info_calls = []
    def info_fn(*args, **kwargs):
        info_calls.append((args, kwargs))
    inst.info = info_fn

    # set initial prompt values (may be used/overwritten)
    inst.prompt = getattr(inst, "prompt", None)
    inst.prompt_as = getattr(inst, "prompt_as", None)

    return inst, dummy_empty, info_calls

def test_do_undo_not_latest_commit():
    commit_hash = "commit-123"
    # state and coder have different last_aider_commit_hash to trigger early return
    inst, dummy_empty, info_calls = setup_basic_gui(
        commit_hash_state="other",
        commit_hash_coder="other",
        io_returns=[[]],  # won't be used
        cmd_undo_fn=lambda arg: (_ for _ in ()).throw(AssertionError("cmd_undo should not be called"))
    )

    # call do_undo
    inst.do_undo(commit_hash)

    # last_undo_empty.empty() must have been called
    assert dummy_empty.called is True

    # info should have been called once with the not-latest message
    assert len(info_calls) == 1
    args, kwargs = info_calls[0]
    assert args and isinstance(args[0], str)
    assert args[0] == f"Commit `{commit_hash}` is not the latest commit."
    assert kwargs == {}

    # state.last_undone_commit_hash should remain None (unchanged)
    assert inst.state.last_undone_commit_hash is None

def test_do_undo_with_reply_sets_prompt_and_informs_lines():
    commit_hash = "commit-abc"
    # io: first call returns ignored value, second call returns list of lines
    io_returns = [[], ["line1", "line2", "line3"]]

    # cmd_undo returns a truthy reply
    def cmd_undo_fn(arg):
        assert arg is None  # as per code: cmd_undo(None)
        return "restored-prompt"

    inst, dummy_empty, info_calls = setup_basic_gui(
        commit_hash_state=commit_hash,
        commit_hash_coder=commit_hash,
        io_returns=io_returns,
        cmd_undo_fn=cmd_undo_fn
    )

    # set initial prompt values to something different to verify they get changed
    inst.prompt = "before"
    inst.prompt_as = "before-as"

    inst.do_undo(commit_hash)

    # last_undo_empty.empty() must have been called
    assert dummy_empty.called is True

    # info should have been called exactly once with processed lines and echo=False
    assert len(info_calls) == 1
    (args, kwargs) = info_calls[0]
    assert 'echo' in kwargs and kwargs['echo'] is False

    # Build expected transformation:
    # lines list -> "\n".join -> splitlines() -> "  \n".join
    original_lines = ["line1", "line2", "line3"]
    joined = "\n".join(original_lines)
    split = joined.splitlines()
    expected = "  \n".join(split)
    assert args[0] == expected

    # last_undone_commit_hash must be set to commit_hash
    assert inst.state.last_undone_commit_hash == commit_hash

    # prompt_as should be set to None and prompt set to reply
    assert inst.prompt_as is None
    assert inst.prompt == "restored-prompt"

def test_do_undo_without_reply_leaves_prompt_intact():
    commit_hash = "commit-xyz"
    io_returns = [[], ["onlyline"]]

    # cmd_undo returns a falsy reply (None)
    def cmd_undo_fn(arg):
        return None

    inst, dummy_empty, info_calls = setup_basic_gui(
        commit_hash_state=commit_hash,
        commit_hash_coder=commit_hash,
        io_returns=io_returns,
        cmd_undo_fn=cmd_undo_fn
    )

    # set initial prompt values to check they remain unchanged
    inst.prompt = "keep-me"
    inst.prompt_as = "keep-as"

    inst.do_undo(commit_hash)

    # last_undo_empty.empty() must have been called
    assert dummy_empty.called is True

    # info called once with processed single line and echo=False
    assert len(info_calls) == 1
    (args, kwargs) = info_calls[0]
    assert kwargs.get('echo') is False
    # For single line "onlyline" the processed result is "onlyline"
    assert args[0] == "onlyline"

    # last_undone_commit_hash must be set
    assert inst.state.last_undone_commit_hash == commit_hash

    # prompt and prompt_as must remain unchanged because reply was falsy
    assert inst.prompt == "keep-me"
    assert inst.prompt_as == "keep-as"
