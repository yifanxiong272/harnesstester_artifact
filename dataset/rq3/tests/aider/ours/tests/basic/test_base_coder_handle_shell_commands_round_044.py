import types
import pytest

import aider.coders.base_coder as base_coder

# We'll call the unbound method Coder.handle_shell_commands with a fake self object
handle = base_coder.Coder.handle_shell_commands


class FakeIO:
    def __init__(self, confirm_responses):
        # confirm_responses: an iterable of booleans to return on successive confirm_ask calls
        self._confirms = list(confirm_responses)
        self.confirm_calls = []
        self.tool_output_calls = []
        self.added_input_history = []
        # simple callable to satisfy signature; record errors passed
        self.tool_error_calls = []

    def confirm_ask(self, prompt, *, subject=None, explicit_yes_required=False, group=None, allow_never=False):
        # record call details exactly as used by the function under test
        self.confirm_calls.append({
            "prompt": prompt,
            "subject": subject,
            "explicit_yes_required": explicit_yes_required,
            "group": group,
            "allow_never": allow_never,
        })
        if not self._confirms:
            # default conservative behavior
            return False
        return self._confirms.pop(0)

    def tool_output(self, msg=None):
        # tool_output is sometimes called without args
        self.tool_output_calls.append(msg)

    def add_to_input_history(self, entry):
        self.added_input_history.append(entry)

    def tool_error(self, *args, **kwargs):
        self.tool_error_calls.append((args, kwargs))


class FakeSelf:
    def __init__(self, io, root="/fake/root"):
        self.io = io
        self.root = root


def test_confirm_false_round_044(monkeypatch):
    """
    If the initial confirm_ask returns False, the function should return None and not run any commands.
    This covers the branch where the user declines running commands (prompt: single command case).
    """
    io = FakeIO(confirm_responses=[False])
    fake = FakeSelf(io)

    # Ensure run_cmd is not accidentally executed: stub that would raise if called
    def _fail_run_cmd(*args, **kwargs):
        raise AssertionError("run_cmd should not be called when user declines confirmation")

    monkeypatch.setattr(base_coder, "run_cmd", _fail_run_cmd)

    result = handle(fake, "echo hi", group=None)

    assert result is None

    # confirm_ask should have been called exactly once with the single-command prompt
    assert len(io.confirm_calls) == 1
    call = io.confirm_calls[0]
    assert call["prompt"] == "Run shell command?"
    # subject should contain the command string
    assert "echo hi" in (call["subject"] or "")


def test_single_command_add_output_round_044(monkeypatch):
    """
    Run a single command, have run_cmd return a single-line output, accept adding the output to chat.
    Verify returned accumulated_output and the final tool_output message with singular 'line'.
    """
    # first confirm: run commands -> True
    # second confirm: add output -> True
    io = FakeIO(confirm_responses=[True, True])
    fake = FakeSelf(io, root="/fake/cwd")

    run_cmd_calls = []

    def fake_run_cmd(cmd, error_print=None, cwd=None):
        # record arguments and return a single-line output
        run_cmd_calls.append({"cmd": cmd, "cwd": cwd})
        # exercise that error_print is passed in: call it with a sample to ensure callable works
        if error_print:
            # don't actually signal an error; just ensure it's callable
            try:
                error_print("no-op")
            except Exception:
                pass
        return 0, "SINGLELINE"

    monkeypatch.setattr(base_coder, "run_cmd", fake_run_cmd)

    result = handle(fake, "echo hi", group="grp")

    # The function should return the accumulated output string when output is added
    assert isinstance(result, str)
    assert "Output from echo hi" in result
    assert "SINGLELINE" in result

    # run_cmd must have been called exactly once with the provided fake root as cwd
    assert len(run_cmd_calls) == 1
    assert run_cmd_calls[0]["cwd"] == fake.root
    assert run_cmd_calls[0]["cmd"] == "echo hi"

    # add_to_input_history should have the /run entry
    assert io.added_input_history == ["/run echo hi"]

    # confirm_ask should have been called twice: first for running, second for adding output
    assert len(io.confirm_calls) == 2
    assert io.confirm_calls[0]["prompt"] == "Run shell command?"
    assert io.confirm_calls[1]["prompt"] == "Add command output to the chat?"

    # The final tool_output call should include the singular 'line' message
    # The function first calls tool_output() with no args, then tool_output(f"Running {command}"), then final message
    assert any(isinstance(m, str) and "Added 1 line of output to the chat." in m for m in io.tool_output_calls), io.tool_output_calls


def test_multiple_commands_plural_round_044(monkeypatch):
    """
    Provide multiple commands including comment/blank lines; ensure only real commands run,
    outputs from multiple commands produce a plural 'lines' final message and correct history additions.
    """
    # accept running and accept adding outputs
    io = FakeIO(confirm_responses=[True, True])
    fake = FakeSelf(io, root="/some/cwd")

    run_cmd_calls = []

    def fake_run_cmd(cmd, error_print=None, cwd=None):
        run_cmd_calls.append((cmd, cwd))
        if cmd.strip() == "echo a":
            return 0, "A"
        if cmd.strip() == "echo b":
            return 0, "B"
        return 0, ""

    monkeypatch.setattr(base_coder, "run_cmd", fake_run_cmd)

    commands_str = "echo a\n# this is a comment\n\n echo b"
    result = handle(fake, commands_str, group=None)

    # Both real commands should have been called in order
    called_cmds = [c for c, cwd in run_cmd_calls]
    assert "echo a" in called_cmds
    assert "echo b" in called_cmds
    assert all(cwd == fake.root for _, cwd in run_cmd_calls)

    # Input history should contain both /run entries in the same order
    assert io.added_input_history == ["/run echo a", "/run echo b"]

    # We accepted adding output, so we should get a returned string containing outputs from both commands
    assert isinstance(result, str)
    assert "Output from echo a" in result
    assert "Output from echo b" in result

    # Final tool_output should indicate 'lines' (plural) and include the correct number
    found_added_msgs = [m for m in io.tool_output_calls if isinstance(m, str) and m.startswith("Added ")]
    assert found_added_msgs, io.tool_output_calls
    # parse number from message like "Added X lines of output to the chat."
    msg = found_added_msgs[-1]
    assert msg.endswith("of output to the chat.")
    assert "lines" in msg
