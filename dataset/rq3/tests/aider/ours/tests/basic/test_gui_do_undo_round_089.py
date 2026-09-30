import types
from types import SimpleNamespace
import pytest

from aider.gui import GUI

# Helpers to build a fake self object compatible with GUI.do_undo
class DummyLastUndoEmpty:
    def __init__(self, container):
        self.container = container
    def empty(self):
        # record that empty was called
        self.container['emptied'] = True

class FakeIO:
    def __init__(self, returns):
        # returns: list of lists to return on successive calls
        self._returns = list(returns)
        self.calls = 0
    def get_captured_lines(self):
        self.calls += 1
        if self._returns:
            return self._returns.pop(0)
        return []

class FakeCommands:
    def __init__(self, io, reply):
        self.io = io
        self._reply = reply
        self.cmd_undo_calls = []
    def cmd_undo(self, arg):
        # record arg and return configured reply
        self.cmd_undo_calls.append(arg)
        return self._reply

class DummyState:
    def __init__(self, last_hash=None):
        self.last_aider_commit_hash = last_hash
        self.last_undone_commit_hash = None

class DummyCoder:
    def __init__(self, last_hash, commands):
        self.last_aider_commit_hash = last_hash
        self.commands = commands

class DummySelf:
    def __init__(self, state_hash, coder_hash, io_returns, cmd_reply):
        self._rec = {}
        self.last_undo_empty = DummyLastUndoEmpty(self._rec)
        self.state = DummyState(state_hash)
        io = FakeIO(io_returns)
        commands = FakeCommands(io, cmd_reply)
        self.coder = DummyCoder(coder_hash, commands)
        # capture calls to info
        self.info_calls = []
        # prompt fields may be set by do_undo
        # they are intentionally not pre-defined unless needed
    def info(self, message, echo=True):
        # normalize message to string for assertions
        self.info_calls.append({'message': message, 'echo': echo})


def _call_do_undo(fake_self, commit_hash):
    # obtain unbound function and call it with our fake self
    func = getattr(GUI, 'do_undo')
    # call the function (unbound) passing fake_self
    return func(fake_self, commit_hash)


def test_do_undo_early_return_when_commit_mismatch_round_089():
    """
    If the provided commit_hash is not the latest on either state or coder,
    do_undo should call last_undo_empty.empty(), call info with the exact
    mismatch message, and return early without calling commands.io.
    """
    # setup: state and coder have latest hash 'abc', but we pass 'wrong'
    fake = DummySelf(state_hash='abc', coder_hash='abc', io_returns=[], cmd_reply=None)

    _call_do_undo(fake, 'wrong')

    # last_undo_empty.empty() must have been called
    assert fake._rec.get('emptied', False) is True

    # info must have been called exactly once with the mismatch message
    assert len(fake.info_calls) == 1
    expected_msg = "Commit `wrong` is not the latest commit."
    assert fake.info_calls[0]['message'] == expected_msg
    # nothing else should have been called on commands.io
    assert fake.coder.commands.io.calls == 0
    # last_undone_commit_hash should remain None because of early return
    assert fake.state.last_undone_commit_hash is None


def test_do_undo_no_reply_sets_last_undone_and_logs_lines_round_089():
    """
    When commit_hash matches, do_undo should capture lines from io, process them
    into a two-line message joined with "  \n", call info with echo=False,
    set last_undone_commit_hash, and not set prompt / prompt_as when reply is falsy.
    """
    # io: first call (ignored) returns ['ignored'], second call returns two lines
    io_returns = [['ignored'], ['L1', 'L2']]
    fake = DummySelf(state_hash='match', coder_hash='match', io_returns=io_returns, cmd_reply=None)

    _call_do_undo(fake, 'match')

    # ensure cmd_undo was called once with None
    assert fake.coder.commands.cmd_undo_calls == [None]

    # info should have been called once for the final lines output
    # (no mismatch info in this path)
    assert len(fake.info_calls) == 1
    expected_message = 'L1  \nL2'  # lines -> join -> splitlines -> join with '  \n'
    assert fake.info_calls[0]['message'] == expected_message
    assert fake.info_calls[0]['echo'] is False

    # last_undone_commit_hash should be set to the commit_hash
    assert fake.state.last_undone_commit_hash == 'match'

    # because reply was falsy (None), do_undo should NOT set prompt or prompt_as
    assert not hasattr(fake, 'prompt')
    assert not hasattr(fake, 'prompt_as')


def test_do_undo_with_reply_sets_prompt_fields_round_089():
    """
    When cmd_undo returns a truthy reply, do_undo should set prompt_as to None
    and prompt to the returned reply, while still logging lines and setting
    last_undone_commit_hash.
    """
    io_returns = [['start'], ['A', 'B', 'C']]
    reply = 'new-prompt-value'
    fake = DummySelf(state_hash='h', coder_hash='h', io_returns=io_returns, cmd_reply=reply)

    _call_do_undo(fake, 'h')

    # info should be called once for the processed lines
    assert len(fake.info_calls) == 1
    assert fake.info_calls[0]['message'] == 'A  \nB  \nC'
    assert fake.info_calls[0]['echo'] is False

    # last_undone_commit_hash should be set
    assert fake.state.last_undone_commit_hash == 'h'

    # because reply was truthy, prompt_as must be set to None and prompt to the reply
    # The method sets attributes on self directly
    assert getattr(fake, 'prompt_as') is None
    assert getattr(fake, 'prompt') == reply
