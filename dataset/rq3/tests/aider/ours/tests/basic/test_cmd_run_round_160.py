import pytest

import aider.commands as commands


class DummyIO:
    def __init__(self, confirm_return=True):
        self._confirm_return = confirm_return
        self.tool_output_calls = []
        self.placeholder = None
        self.confirm_asks = []
        # Provide a callable attribute expected by cmd_run
        self.tool_error = lambda *args, **kwargs: None

    def confirm_ask(self, prompt):
        # Record the prompt and return the preconfigured answer
        self.confirm_asks.append(prompt)
        return self._confirm_return

    def tool_output(self, msg):
        self.tool_output_calls.append(msg)


class DummyModel:
    def __init__(self, token_count_value):
        self._tc = token_count_value

    def token_count(self, s):
        return self._tc


class DummyCoder:
    def __init__(self, token_count_value):
        self.main_model = DummyModel(token_count_value)
        self.root = "/fake/root"
        self.cur_messages = []


def make_commands_instance(io_obj, coder_obj):
    # Avoid calling Commands.__init__ which has complex side effects.
    cmd = object.__new__(commands.Commands)
    cmd.verbose = False
    cmd.io = io_obj
    cmd.coder = coder_obj
    return cmd


def test_cmd_run_no_output_round_160(monkeypatch):
    """
    If run_cmd returns combined_output = None, cmd_run should return None and
    should NOT call token_count nor prompt the user.
    """
    # Arrange
    io = DummyIO(confirm_return=True)

    class RaisingModel:
        def token_count(self, s):
            raise AssertionError("token_count should not be called when output is None")

    # Use DummyCoder so attributes can be replaced if needed
    coder = DummyCoder(token_count_value=0)
    coder.main_model = RaisingModel()

    instance = make_commands_instance(io, coder)

    def fake_run_cmd(args, verbose=None, error_print=None, cwd=None):
        return (0, None)

    monkeypatch.setattr(commands, "run_cmd", fake_run_cmd)

    # Act
    result = commands.Commands.cmd_run(instance, "echo hi", add_on_nonzero_exit=False)

    # Assert
    assert result is None
    assert io.confirm_asks == []
    assert coder.cur_messages == []


def test_cmd_run_add_on_nonzero_exit_returns_msg_round_160(monkeypatch):
    """
    When add_on_nonzero_exit is True and exit_status != 0, the function
    should add the output to the chat and return the formatted message.
    """
    io = DummyIO(confirm_return=False)  # confirm_ask should not be used in this path
    coder = DummyCoder(token_count_value=2000)
    instance = make_commands_instance(io, coder)

    # Provide a predictable format for the run_output template
    monkeypatch.setattr(commands.prompts, "run_output", "RUN:{command}|OUT:{output}")

    def fake_run_cmd(args, verbose=None, error_print=None, cwd=None):
        return (2, "a\nb\n")

    monkeypatch.setattr(commands, "run_cmd", fake_run_cmd)

    # Act
    result = commands.Commands.cmd_run(instance, "echo hi", add_on_nonzero_exit=True)

    # Assert
    expected_msg = "RUN:echo hi|OUT:a\nb\n"
    assert result == expected_msg

    # Should have announced added lines (2 lines)
    assert io.tool_output_calls == ["Added 2 lines of output to the chat."]

    # cur_messages should get the user message and an assistant ack
    assert len(coder.cur_messages) == 2
    assert coder.cur_messages[0]["role"] == "user"
    assert coder.cur_messages[0]["content"] == expected_msg
    assert coder.cur_messages[1] == {"role": "assistant", "content": "Ok."}


def test_cmd_run_confirm_add_sets_placeholder_round_160(monkeypatch):
    """
    When add_on_nonzero_exit is False, confirm_ask returns True, and exit_status != 0,
    the function should add the output and set the io.placeholder to the expected
    troubleshooting prompt, returning None.
    """
    io = DummyIO(confirm_return=True)
    coder = DummyCoder(token_count_value=1000)
    instance = make_commands_instance(io, coder)

    monkeypatch.setattr(commands.prompts, "run_output", "RUN:{command}|OUT:{output}")

    def fake_run_cmd(args, verbose=None, error_print=None, cwd=None):
        return (1, "onlyline\n")

    monkeypatch.setattr(commands, "run_cmd", fake_run_cmd)

    # Act
    result = commands.Commands.cmd_run(instance, "somecmd", add_on_nonzero_exit=False)

    # Assert
    assert result is None
    # placeholder should be set because exit_status != 0 and add_on_nonzero_exit is False
    assert io.placeholder == "What's wrong? Fix"

    # Confirm tool output and messages were added (1 line -> singular 'line')
    assert io.tool_output_calls == ["Added 1 line of output to the chat."]
    assert len(coder.cur_messages) == 2
    assert coder.cur_messages[0]["role"] == "user"
    assert "onlyline" in coder.cur_messages[0]["content"]
    assert coder.cur_messages[1]["content"] == "Ok."

    # confirm_ask prompt should include the computed token count formatted as '1.0k'
    assert io.confirm_asks, "confirm_ask was expected to be called"
    assert io.confirm_asks[0].startswith("Add ") and "k tokens" in io.confirm_asks[0]
    assert "1.0k" in io.confirm_asks[0]


def test_cmd_run_confirm_add_exit_zero_no_placeholder_round_160(monkeypatch):
    """
    When confirm_ask returns True and exit_status == 0, output should be added
    but no placeholder should be set; function returns None.
    """
    io = DummyIO(confirm_return=True)
    coder = DummyCoder(token_count_value=3000)
    instance = make_commands_instance(io, coder)

    monkeypatch.setattr(commands.prompts, "run_output", "RUN:{command}|OUT:{output}")

    def fake_run_cmd(args, verbose=None, error_print=None, cwd=None):
        return (0, "x\ny\nz\n")

    monkeypatch.setattr(commands, "run_cmd", fake_run_cmd)

    # Act
    result = commands.Commands.cmd_run(instance, "cmd", add_on_nonzero_exit=False)

    # Assert
    assert result is None
    # Because exit status is 0, placeholder shouldn't be set
    assert io.placeholder is None
    # Should have announced added 3 lines
    assert io.tool_output_calls == ["Added 3 lines of output to the chat."]
    assert len(coder.cur_messages) == 2
    assert coder.cur_messages[1]["content"] == "Ok."
