# file: aider/commands.py:1003-1043
# asked: {"lines": [1010, 1019, 1039, 1040, 1043], "branches": [[1009, 1010], [1016, 1019], [1021, 1043], [1036, 1039], [1039, 1040], [1039, 1043]]}
# gained: {"lines": [1010, 1019, 1039, 1040, 1043], "branches": [[1009, 1010], [1016, 1019], [1036, 1039], [1039, 1040], [1039, 1043]]}

import types
from types import SimpleNamespace

import pytest

import aider.commands as commands_mod
from aider.commands import Commands


def bind_cmd_run(instance):
    # Bind the unbound function to our fake instance
    return Commands.cmd_run.__get__(instance, Commands)


def make_fake_io(confirm_ret=True):
    calls = {}

    def tool_error(*args, **kwargs):
        calls.setdefault("tool_error", []).append((args, kwargs))

    def confirm_ask(prompt):
        calls.setdefault("confirm_ask", []).append(prompt)
        return confirm_ret

    def tool_output(msg):
        calls.setdefault("tool_output", []).append(msg)

    io = SimpleNamespace(
        tool_error=tool_error,
        confirm_ask=confirm_ask,
        tool_output=tool_output,
        placeholder=None,
    )
    io._calls = calls
    return io


def make_fake_coder(token_count_ret):
    main_model = SimpleNamespace(token_count=lambda s: token_count_ret)
    coder = SimpleNamespace(root="/tmp", main_model=main_model, cur_messages=[])
    return coder


def test_cmd_run_returns_on_none_output(monkeypatch):
    """
    Exercise the branch where combined_output is None and the function returns early.
    This should execute the 'if combined_output is None: return' line.
    """
    fake_io = make_fake_io(confirm_ret=False)
    fake_coder = make_fake_coder(token_count_ret=0)

    fake_inst = SimpleNamespace(verbose=True, io=fake_io, coder=fake_coder)

    # Stub run_cmd to return (0, None)
    def fake_run_cmd(args, verbose, error_print, cwd):
        assert verbose is True
        assert cwd == fake_coder.root
        # ensure error_print is the io.tool_error callable
        assert error_print is fake_io.tool_error
        return 0, None

    monkeypatch.setattr(commands_mod, "run_cmd", fake_run_cmd)

    # Bind and call
    cmd = bind_cmd_run(fake_inst)
    ret = cmd("doesn't matter", add_on_nonzero_exit=False)

    assert ret is None
    # confirm_ask should not have been called
    assert "confirm_ask" not in fake_io._calls


def test_cmd_run_adds_output_on_confirm_and_zero_exit(monkeypatch):
    """
    Exercise the path where add_on_nonzero_exit is False, confirm_ask returns True,
    and exit_status == 0. This hits the branch where add = self.io.confirm_ask(...)
    and then the code that appends messages and reports tool_output.
    """
    combined_output = "first line\nsecond line\n"
    token_count = 1500  # -> 1.5k tokens -> prompt uses 1.5k

    fake_io = make_fake_io(confirm_ret=True)
    fake_coder = make_fake_coder(token_count_ret=token_count)

    fake_inst = SimpleNamespace(verbose=False, io=fake_io, coder=fake_coder)

    # Stub run_cmd to return success and the combined_output
    def fake_run_cmd(args, verbose, error_print, cwd):
        assert verbose is False
        assert cwd == fake_coder.root
        return 0, combined_output

    monkeypatch.setattr(commands_mod, "run_cmd", fake_run_cmd)

    # Monkeypatch prompts.run_output template used to format the added message
    monkeypatch.setattr(commands_mod.prompts, "run_output", "CMD: {command}\nOUT:{output}")

    cmd = bind_cmd_run(fake_inst)
    ret = cmd("echo hi", add_on_nonzero_exit=False)

    # Should return None because exit_status == 0 and nothing else to return
    assert ret is None

    # confirm_ask was called with the expected formatted token string
    prompts_called = fake_io._calls.get("confirm_ask")
    assert prompts_called is not None and len(prompts_called) == 1
    expected_prompt = "Add 1.5k tokens of command output to the chat?"
    assert prompts_called[0] == expected_prompt

    # tool_output called with the expected added lines message
    tool_outputs = fake_io._calls.get("tool_output")
    assert tool_outputs is not None and len(tool_outputs) == 1
    assert tool_outputs[0] == "Added 2 lines of output to the chat."

    # cur_messages should have two appended messages: user with formatted run_output and assistant "Ok."
    assert len(fake_coder.cur_messages) == 2
    user_msg = fake_coder.cur_messages[-2]
    assistant_msg = fake_coder.cur_messages[-1]
    assert user_msg["role"] == "user"
    assert "CMD: echo hi" in user_msg["content"]
    assert "OUT:first line" in user_msg["content"]
    assert assistant_msg == {"role": "assistant", "content": "Ok."}
    # placeholder should remain unchanged (None)
    assert fake_io.placeholder is None


def test_cmd_run_sets_placeholder_on_nonzero_exit_with_add(monkeypatch):
    """
    Exercise the branch: add_on_nonzero_exit False, confirm_ask True, exit_status != 0.
    This should set io.placeholder to "What's wrong? Fix" and return None.
    This covers the 'elif add and exit_status != 0' branch.
    """
    combined_output = "only line\n"
    token_count = 1000  # -> 1.0k tokens

    fake_io = make_fake_io(confirm_ret=True)
    fake_coder = make_fake_coder(token_count_ret=token_count)

    fake_inst = SimpleNamespace(verbose=False, io=fake_io, coder=fake_coder)

    # Stub run_cmd to return non-zero exit status
    def fake_run_cmd(args, verbose, error_print, cwd):
        return 2, combined_output

    monkeypatch.setattr(commands_mod, "run_cmd", fake_run_cmd)

    # Use a simple run_output template
    monkeypatch.setattr(commands_mod.prompts, "run_output", "{command}:{output}")

    cmd = bind_cmd_run(fake_inst)
    ret = cmd("failcmd", add_on_nonzero_exit=False)

    # When add is True and exit status != 0, function should ultimately return None
    assert ret is None

    # placeholder set to prompt for fixing
    assert fake_io.placeholder == "What's wrong? Fix"

    # Messages added
    assert len(fake_coder.cur_messages) == 2
    assert fake_coder.cur_messages[-2]["role"] == "user"
    assert "failcmd" in fake_coder.cur_messages[-2]["content"]
    assert fake_coder.cur_messages[-1] == {"role": "assistant", "content": "Ok."}
