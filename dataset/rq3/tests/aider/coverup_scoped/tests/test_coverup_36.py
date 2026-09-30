# file: aider/gui.py:498-521
# asked: {"lines": [498, 499, 502, 503, 505, 506, 508, 509, 510, 512, 513, 514, 515, 517, 519, 520, 521], "branches": [[501, 505], [501, 508], [519, 0], [519, 520]]}
# gained: {"lines": [498, 499, 502, 503, 505, 506, 508, 509, 510, 512, 513, 514, 515, 517, 519, 520, 521], "branches": [[501, 505], [501, 508], [519, 0], [519, 520]]}

import types
import builtins
import pytest

from aider.gui import GUI


class DummyEmpty:
    def __init__(self):
        self.called = False

    def empty(self):
        self.called = True


class DummyIO:
    def __init__(self, lines, call_recorder):
        # lines to return
        self._lines = list(lines)
        self.call_recorder = call_recorder

    def get_captured_lines(self):
        # record call and return a shallow copy to simulate realistic behavior
        self.call_recorder.append("get_captured_lines")
        return list(self._lines)


class DummyCommands:
    def __init__(self, io_obj, reply, cmd_recorder):
        self.io = io_obj
        self._reply = reply
        self.cmd_recorder = cmd_recorder

    def cmd_undo(self, arg):
        # record that cmd_undo was called with the provided arg
        self.cmd_recorder.append(arg)
        return self._reply


class DummyCoder:
    def __init__(self, last_aider_commit_hash, commands):
        self.last_aider_commit_hash = last_aider_commit_hash
        self.commands = commands


class DummyState:
    def __init__(self, last_aider_commit_hash=None):
        self.last_aider_commit_hash = last_aider_commit_hash
        self.last_undone_commit_hash = None


def make_gui_instance():
    # Create a GUI instance without calling its __init__
    gui = object.__new__(GUI)
    # attach attributes that do_undo will access
    gui.last_undo_empty = DummyEmpty()
    gui.state = DummyState()
    gui.coder = None  # set by tests
    # capture info calls as list of tuples (msg, echo)
    gui._info_calls = []
    # define info method accepting (msg, echo=True)
    gui.info = lambda msg, echo=True: gui._info_calls.append((msg, echo))
    # default prompt attributes
    gui.prompt_as = "INITIAL_PROMPT_AS"
    gui.prompt = "INITIAL_PROMPT"
    return gui


def test_do_undo_not_latest_commit():
    gui = make_gui_instance()
    commit_hash = "abc123"

    # state and coder disagree with commit_hash to force early return
    gui.state.last_aider_commit_hash = "other"
    # coder present but with different last_aider_commit_hash
    dummy_io = DummyIO([], [])
    dummy_commands = DummyCommands(dummy_io, None, [])
    gui.coder = DummyCoder(last_aider_commit_hash="other-too", commands=dummy_commands)

    # ensure last_undone_commit_hash is initially None
    assert gui.state.last_undone_commit_hash is None

    # call the method under test
    gui.do_undo(commit_hash)

    # last_undo_empty.empty must have been called
    assert gui.last_undo_empty.called is True

    # info must have been called once with the not-latest message
    assert len(gui._info_calls) == 1
    msg, echo = gui._info_calls[0]
    assert commit_hash in msg
    # early-return path uses default echo which is True
    assert echo is True

    # ensure last_undone_commit_hash remains unchanged (still None)
    assert gui.state.last_undone_commit_hash is None

    # ensure cmd_undo was not called (cmd_recorder empty)
    assert dummy_commands.cmd_recorder == []


def test_do_undo_matches_no_reply():
    gui = make_gui_instance()
    commit_hash = "match-commit"

    # set state and coder to match commit_hash
    gui.state.last_aider_commit_hash = commit_hash

    # prepare io to return lines and record calls
    io_calls = []
    dummy_io = DummyIO(["line1", "line2"], io_calls)
    cmd_calls = []
    dummy_commands = DummyCommands(dummy_io, None, cmd_calls)
    gui.coder = DummyCoder(last_aider_commit_hash=commit_hash, commands=dummy_commands)

    # ensure initial prompts are something different so we can assert unchanged
    gui.prompt_as = "SOMETHING"
    gui.prompt = "SOMETHING_ELSE"

    gui.do_undo(commit_hash)

    # last_undo_empty must have been called
    assert gui.last_undo_empty.called is True

    # get_captured_lines should have been called twice (before and after cmd_undo)
    assert io_calls.count("get_captured_lines") == 2

    # cmd_undo should have been called once with argument None
    assert cmd_calls == [None]

    # info was called twice overall: once for early message? No - in this path only the second info call with lines
    # The first info (not-latest) is not expected. We expect exactly one info call with the transformed lines.
    assert len(gui._info_calls) == 1
    msg, echo = gui._info_calls[0]

    # verify the transformed lines: join -> splitlines -> join with '  \n'
    expected = "line1  \nline2"
    assert msg == expected
    assert echo is False

    # last_undone_commit_hash must have been set to commit_hash
    assert gui.state.last_undone_commit_hash == commit_hash

    # since cmd_undo returned a falsy value, prompt and prompt_as remain unchanged
    assert gui.prompt_as == "SOMETHING"
    assert gui.prompt == "SOMETHING_ELSE"


def test_do_undo_matches_with_reply():
    gui = make_gui_instance()
    commit_hash = "match-commit-2"

    # set state and coder to match commit_hash
    gui.state.last_aider_commit_hash = commit_hash

    # prepare io to return a single line and record calls
    io_calls = []
    dummy_io = DummyIO(["onlyline"], io_calls)
    cmd_calls = []
    reply_text = "UNDO_REPLY"
    dummy_commands = DummyCommands(dummy_io, reply_text, cmd_calls)
    gui.coder = DummyCoder(last_aider_commit_hash=commit_hash, commands=dummy_commands)

    # set prompts to some pre-existing values to see them overwritten
    gui.prompt_as = "WILL_BE_CLEARED"
    gui.prompt = "OLD_PROMPT"

    gui.do_undo(commit_hash)

    # ensure io called twice
    assert io_calls.count("get_captured_lines") == 2

    # cmd_undo called once with None
    assert cmd_calls == [None]

    # info called once with transformed single-line (splitlines of single line is same) and echo=False
    assert len(gui._info_calls) == 1
    msg, echo = gui._info_calls[0]
    # single line -> expected is same line (no extra separators)
    assert msg == "onlyline"
    assert echo is False

    # last_undone_commit_hash updated
    assert gui.state.last_undone_commit_hash == commit_hash

    # because reply was truthy, prompt_as should be set to None and prompt to reply_text
    assert gui.prompt_as is None
    assert gui.prompt == reply_text
