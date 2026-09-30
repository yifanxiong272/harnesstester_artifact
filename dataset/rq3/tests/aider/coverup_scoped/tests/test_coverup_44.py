# file: aider/commands.py:312-332
# asked: {"lines": [314, 315, 319, 325, 326, 327, 328, 329, 330, 332], "branches": [[313, 314], [318, 319], [321, 325], [325, 326], [325, 329], [329, 330], [329, 332]]}
# gained: {"lines": [314, 315, 319, 325, 326, 327, 328, 329, 330, 332], "branches": [[313, 314], [318, 319], [321, 325], [325, 326], [325, 329], [329, 330], [329, 332]]}

import pytest
from unittest.mock import Mock

from aider.commands import Commands


def test_run_bang_prefix_calls_do_run_and_events():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    # prepare mocks
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io
    called = {}

    def fake_do_run(command, rest):
        called['command'] = command
        called['rest'] = rest
        return "did:" + command + ":" + rest

    cmd.do_run = Mock(side_effect=fake_do_run)

    result = cmd.run("!echo hello")
    assert result == "did:run:echo hello"
    cmd.coder.event.assert_called_once_with("command_run")
    # ensure do_run was called with the expected args
    assert called['command'] == "run"
    assert called['rest'] == "echo hello"


def test_run_returns_none_when_matching_none_and_no_side_effects():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io
    cmd.do_run = Mock()
    # matching_commands returns None to trigger early return
    cmd.matching_commands = lambda inp: None

    result = cmd.run("some input")
    assert result is None
    cmd.coder.event.assert_not_called()
    cmd.do_run.assert_not_called()


def test_run_single_matching_triggers_command_and_do_run():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io

    # matching_commands returns a single match
    cmd.matching_commands = lambda inp: (["/foo"], "/foo", "argument1 argument2")
    cmd.do_run = Mock(return_value="executed foo")

    result = cmd.run("whatever")
    assert result == "executed foo"
    cmd.coder.event.assert_called_once_with("command_foo")
    cmd.do_run.assert_called_once_with("foo", "argument1 argument2")


def test_run_first_word_in_matching_uses_first_word_command():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io

    # multiple possible commands but first_word is one of them
    cmd.matching_commands = lambda inp: (["/alpha", "/beta"], "/beta", "restargs")
    cmd.do_run = Mock(return_value="beta ran")

    result = cmd.run("something")
    assert result == "beta ran"
    cmd.coder.event.assert_called_once_with("command_beta")
    cmd.do_run.assert_called_once_with("beta", "restargs")


def test_run_ambiguous_reports_tool_error_and_no_do_run():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io
    cmd.io.tool_error = Mock()

    # ambiguous: multiple matches and first_word not in the list
    cmd.matching_commands = lambda inp: (["/one", "/two"], "/three", "x")
    cmd.do_run = Mock()

    result = cmd.run("ambiguous")
    # run returns None (no explicit return), but tool_error should be called
    assert result is None
    cmd.io.tool_error.assert_called_once_with("Ambiguous command: /one, /two")
    cmd.coder.event.assert_not_called()
    cmd.do_run.assert_not_called()


def test_run_invalid_reports_tool_error_when_no_matching_commands():
    io = Mock()
    coder = Mock()
    cmd = Commands(io, coder)
    cmd.coder = coder
    cmd.coder.event = Mock()
    cmd.io = io
    cmd.io.tool_error = Mock()

    # invalid: empty matching_commands list
    cmd.matching_commands = lambda inp: ([], "/nope", "rest")
    cmd.do_run = Mock()

    result = cmd.run("invalid")
    assert result is None
    cmd.io.tool_error.assert_called_once_with("Invalid command: /nope")
    cmd.coder.event.assert_not_called()
    cmd.do_run.assert_not_called()
