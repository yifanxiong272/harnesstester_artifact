# file: aider/commands.py:312-332
# asked: {"lines": [314, 315, 319, 325, 326, 327, 328, 329, 330, 332], "branches": [[313, 314], [318, 319], [321, 325], [325, 326], [325, 329], [329, 330], [329, 332]]}
# gained: {"lines": [314, 315, 319, 325, 326, 327, 328, 329, 330, 332], "branches": [[313, 314], [318, 319], [321, 325], [325, 326], [325, 329], [329, 330], [329, 332]]}

import pytest
from types import SimpleNamespace

from aider.commands import Commands


class DummyCoder:
    def __init__(self):
        self.events = []

    def event(self, name):
        self.events.append(name)


class DummyIO:
    def __init__(self):
        self.errors = []

    def tool_error(self, msg):
        self.errors.append(msg)


def make_commands_instance():
    io = DummyIO()
    coder = DummyCoder()
    return Commands(io=io, coder=coder), io, coder


def test_run_bang_command_calls_event_and_do_run(monkeypatch):
    cmds, io, coder = make_commands_instance()

    recorded = {}

    def fake_do_run(cmd, args):
        recorded['called'] = (cmd, args)
        return "RESULT"

    # Replace do_run with our fake
    monkeypatch.setattr(cmds, "do_run", fake_do_run)

    result = cmds.run("!echo hello")

    assert result == "RESULT"
    assert coder.events == ["command_run"]
    assert recorded['called'] == ("run", "echo hello")


def test_run_matching_none_returns_none(monkeypatch):
    cmds, io, coder = make_commands_instance()

    # matching_commands returns None -> run should return None and not call coder.event
    monkeypatch.setattr(cmds, "matching_commands", lambda inp: None)
    # Also ensure do_run would raise if called (should not be called)
    monkeypatch.setattr(cmds, "do_run", lambda cmd, args: (_ for _ in ()).throw(RuntimeError("do_run called")))

    result = cmds.run("/anything")
    assert result is None
    assert coder.events == []


def test_run_single_matching_command_calls_event_and_do_run(monkeypatch):
    cmds, io, coder = make_commands_instance()

    # matching_commands returns one matching command
    monkeypatch.setattr(cmds, "matching_commands", lambda inp: (["/single"], "/single", "rest args"))

    called = {}

    def fake_do_run(cmd, args):
        called['args'] = (cmd, args)
        return "SINGLE_OK"

    monkeypatch.setattr(cmds, "do_run", fake_do_run)

    res = cmds.run("/single rest args")
    assert res == "SINGLE_OK"
    # command extracted should be without leading '/'
    assert coder.events == ["command_single"]
    assert called['args'] == ("single", "rest args")


def test_run_first_word_in_matching_commands_branch(monkeypatch):
    cmds, io, coder = make_commands_instance()

    # Prepare a case where multiple matching commands exist and first_word is in them
    monkeypatch.setattr(cmds, "matching_commands", lambda inp: (["/a", "/b"], "/b", "R"))

    called = {}

    def fake_do_run(cmd, args):
        called['args'] = (cmd, args)
        return "FIRSTWORD_OK"

    monkeypatch.setattr(cmds, "do_run", fake_do_run)

    res = cmds.run("/b R")
    assert res == "FIRSTWORD_OK"
    assert coder.events == ["command_b"]
    assert called['args'] == ("b", "R")


def test_run_ambiguous_and_invalid_commands_call_tool_error(monkeypatch):
    cmds, io, coder = make_commands_instance()

    # Ambiguous: multiple matches and first_word not in matching_commands
    monkeypatch.setattr(cmds, "matching_commands", lambda inp: (["/one", "/two"], "/maybe", ""))
    res = cmds.run("/maybe ")
    assert res is None
    # io.tool_error should have been called with ambiguous message listing the commands
    assert len(io.errors) == 1
    assert "Ambiguous command" in io.errors[0]
    assert "/one" in io.errors[0] and "/two" in io.errors[0]

    # Reset errors
    io.errors.clear()

    # Invalid: zero matching commands -> should trigger invalid branch
    monkeypatch.setattr(cmds, "matching_commands", lambda inp: ([], "/nope", ""))
    res2 = cmds.run("/nope ")
    assert res2 is None
    assert len(io.errors) == 1
    assert "Invalid command: /nope" == io.errors[0]
