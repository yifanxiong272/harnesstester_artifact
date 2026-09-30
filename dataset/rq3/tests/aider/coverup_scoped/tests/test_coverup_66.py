# file: aider/commands.py:1003-1043
# asked: {"lines": [1010, 1019, 1039, 1040, 1043], "branches": [[1009, 1010], [1016, 1019], [1021, 1043], [1036, 1039], [1039, 1040], [1039, 1043]]}
# gained: {"lines": [1010, 1019, 1039, 1040, 1043], "branches": [[1009, 1010], [1016, 1019], [1036, 1039], [1039, 1040]]}

import pytest

from aider import prompts
import aider.commands as commands_module
from aider.commands import Commands


class DummyIO:
    def __init__(self, confirm_response=False):
        self.tool_errors = []
        self.outputs = []
        self.confirm_response = confirm_response
        self.placeholder = None

    def tool_error(self, *args, **kwargs):
        self.tool_errors.append((args, kwargs))

    def confirm_ask(self, prompt):
        # Return the pre-set response and record the prompt
        self.last_confirm_prompt = prompt
        return self.confirm_response

    def tool_output(self, msg):
        self.outputs.append(msg)


class DummyMainModel:
    def __init__(self, token_count_return=1000):
        self._token_count_return = token_count_return

    def token_count(self, text):
        # Return a predictable token count
        return self._token_count_return


class DummyCoder:
    def __init__(self, token_count_return=1000):
        self.root = "/tmp"
        self.main_model = DummyMainModel(token_count_return)
        self.cur_messages = []


def test_cmd_run_returns_when_combined_output_none(monkeypatch):
    # Arrange
    def fake_run_cmd(args, verbose, error_print, cwd):
        return 0, None

    monkeypatch.setattr(commands_module, "run_cmd", fake_run_cmd)

    io = DummyIO()
    coder = DummyCoder()
    cmd = Commands(io, coder, verbose=False)

    # Act
    result = cmd.cmd_run("doesn't matter", add_on_nonzero_exit=False)

    # Assert: early return (None) and no messages added
    assert result is None
    assert cmd.coder.cur_messages == []
    assert cmd.io.outputs == []
    assert cmd.io.placeholder is None


def test_cmd_run_add_on_nonzero_exit_returns_msg_and_appends_messages(monkeypatch):
    # Arrange: run_cmd returns non-zero exit status and some output
    combined_output = "first line\nsecond line\n"
    exit_status = 1

    def fake_run_cmd(args, verbose, error_print, cwd):
        return exit_status, combined_output

    monkeypatch.setattr(commands_module, "run_cmd", fake_run_cmd)

    io = DummyIO(confirm_response=False)
    coder = DummyCoder(token_count_return=2000)  # token_count used to compute k_tokens
    cmd = Commands(io, coder, verbose=True)
    # Ensure cur_messages starts empty
    assert cmd.coder.cur_messages == []

    # Act: add_on_nonzero_exit True should cause add=True and immediately return the formatted msg
    result = cmd.cmd_run("mycmd --fail", add_on_nonzero_exit=True)

    # Build expected message using same template logic as code
    expected_msg = prompts.run_output.format(command="mycmd --fail", output=combined_output)

    # Assert: function returns the formatted msg
    assert result == expected_msg

    # Assert: messages were appended
    assert len(cmd.coder.cur_messages) == 2
    assert cmd.coder.cur_messages[0]["role"] == "user"
    assert cmd.coder.cur_messages[0]["content"] == expected_msg
    assert cmd.coder.cur_messages[1]["role"] == "assistant"
    assert cmd.coder.cur_messages[1]["content"] == "Ok."

    # Assert: tool_output was called with correct pluralization (2 lines)
    assert any("Added 2 lines of output to the chat." in o for o in cmd.io.outputs)

    # Placeholder should remain unchanged (not set in this branch)
    assert cmd.io.placeholder is None


def test_cmd_run_confirm_add_and_nonzero_sets_placeholder(monkeypatch):
    # Arrange: run_cmd returns non-zero exit status and single-line output
    combined_output = "only one line\n"
    exit_status = 2

    def fake_run_cmd(args, verbose, error_print, cwd):
        return exit_status, combined_output

    monkeypatch.setattr(commands_module, "run_cmd", fake_run_cmd)

    # io.confirm_ask should return True to trigger the 'add' branch via confirm_ask (line 1019)
    io = DummyIO(confirm_response=True)
    coder = DummyCoder(token_count_return=500)  # arbitrary
    cmd = Commands(io, coder, verbose=False)

    # Act: add_on_nonzero_exit False so confirm_ask is used
    result = cmd.cmd_run("somecmd", add_on_nonzero_exit=False)

    # Assert: function returns None (since this branch sets placeholder but doesn't return msg)
    assert result is None

    # Assert: messages appended
    assert len(cmd.coder.cur_messages) == 2
    expected_msg = prompts.run_output.format(command="somecmd", output=combined_output)
    assert cmd.coder.cur_messages[0]["content"] == expected_msg
    assert cmd.coder.cur_messages[1]["content"] == "Ok."

    # Assert: tool_output called with proper singular "line"
    assert any("Added 1 line of output to the chat." in o for o in io.outputs)

    # Assert: placeholder was set by the branch at 1039-1040
    assert io.placeholder == "What's wrong? Fix"
