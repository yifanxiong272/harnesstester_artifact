# file: aider/coders/base_coder.py:2450-2485
# asked: {"lines": [2451, 2452, 2453, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2463, 2465, 2466, 2467, 2468, 2469, 2471, 2472, 2474, 2475, 2476, 2477, 2479, 2480, 2482, 2483, 2484, 2485], "branches": [[2456, 2463], [2456, 2465], [2466, 2467], [2466, 2479], [2468, 2469], [2468, 2471], [2476, 2466], [2476, 2477], [2479, 0], [2479, 2482]]}
# gained: {"lines": [2451, 2452, 2453, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2463, 2465, 2466, 2467, 2468, 2469, 2471, 2472, 2474, 2475, 2476, 2477, 2479, 2480, 2482, 2483, 2484, 2485], "branches": [[2456, 2463], [2456, 2465], [2466, 2467], [2466, 2479], [2468, 2469], [2468, 2471], [2476, 2477], [2479, 0], [2479, 2482]]}

import types
import importlib

import pytest


class FakeIO:
    def __init__(self, confirm_responses):
        # confirm_responses: list of booleans to return on successive confirm_ask calls
        self.confirm_responses = list(confirm_responses)
        self.confirm_calls = []
        self.tool_outputs = []
        self.input_history = []
        self.error_prints = []

    def confirm_ask(self, prompt, subject=None, explicit_yes_required=False, group=None, allow_never=False):
        # record the call
        self.confirm_calls.append(
            {
                "prompt": prompt,
                "subject": subject,
                "explicit_yes_required": explicit_yes_required,
                "group": group,
                "allow_never": allow_never,
            }
        )
        if not self.confirm_responses:
            return False
        return self.confirm_responses.pop(0)

    def tool_output(self, msg=None):
        self.tool_outputs.append(msg)

    def add_to_input_history(self, s):
        self.input_history.append(s)

    def tool_error(self, *args, **kwargs):
        self.error_prints.append((args, kwargs))


def _bind_handle(base_module, instance):
    # Bind the Coder.handle_shell_commands function to a lightweight instance
    func = base_module.Coder.handle_shell_commands
    return types.MethodType(func, instance)


def test_handle_shell_commands_initial_cancel(monkeypatch):
    """
    If the initial confirm_ask returns False, nothing should run and the method should return None.
    """
    base_mod = importlib.import_module("aider.coders.base_coder")

    # Prepare fake IO that returns False on the first confirm_ask
    fake_io = FakeIO(confirm_responses=[False])

    # lightweight instance to avoid calling Coder.__init__
    class Dummy:
        pass

    inst = Dummy()
    inst.io = fake_io
    inst.root = "/some/root"

    # Ensure run_cmd is not called; set a stub that would raise if invoked
    def run_cmd_not_expected(cmd, error_print=None, cwd=None):
        raise AssertionError("run_cmd should not be called when user cancels")

    monkeypatch.setattr(base_mod, "run_cmd", run_cmd_not_expected)

    bound = _bind_handle(base_mod, inst)

    result = bound("echo hello\n", group="g1")

    assert result is None
    # confirm_ask should have been called once with the prompt appropriate for one command
    assert len(fake_io.confirm_calls) == 1
    call = fake_io.confirm_calls[0]
    assert call["prompt"] in ("Run shell command?", "Run shell commands?")
    # subject should include the command we passed
    assert "echo hello" in call["subject"]


def test_handle_shell_commands_runs_and_adds_output(monkeypatch):
    """
    When the user confirms, run_cmd should be invoked for non-comment lines,
    accumulated output should be returned when the second confirm_ask returns True,
    and tool_output should report the number of lines added.
    """
    base_mod = importlib.import_module("aider.coders.base_coder")

    # Prepare fake IO: first confirm True (run commands), second confirm True (add output)
    fake_io = FakeIO(confirm_responses=[True, True])

    class Dummy:
        pass

    inst = Dummy()
    inst.io = fake_io
    inst.root = "/tmp/repo"

    # Capture run_cmd calls and return a sample output
    run_cmd_calls = []

    def run_cmd_stub(cmd, error_print=None, cwd=None):
        run_cmd_calls.append({"cmd": cmd, "cwd": cwd})
        # do not invoke error_print since status is success
        return 0, "hello-world\n"

    monkeypatch.setattr(base_mod, "run_cmd", run_cmd_stub)

    bound = _bind_handle(base_mod, inst)

    # Include blank lines and comments to exercise skipping logic
    commands = "\n# this is a comment\n\necho hi\n"
    result = bound(commands, group="groupA")

    # Result should be the accumulated output string
    assert result is not None
    assert "Output from echo hi" in result
    assert "hello-world" in result

    # run_cmd should have been called once for the real command
    assert len(run_cmd_calls) == 1
    assert run_cmd_calls[0]["cmd"] == "echo hi"
    assert run_cmd_calls[0]["cwd"] == inst.root

    # The input history should have the /run command recorded
    assert "/run echo hi" in fake_io.input_history

    # The tool_output list should include the final "Added N lines of output to the chat." message.
    # Determine expected number of lines
    num_lines = len(result.strip().splitlines())
    line_plural = "line" if num_lines == 1 else "lines"
    expected_msg = f"Added {num_lines} {line_plural} of output to the chat."
    assert expected_msg in fake_io.tool_outputs


def test_handle_shell_commands_runs_but_does_not_add_when_declined(monkeypatch):
    """
    When the user confirms running commands but declines to add output, the function should return None
    and no "Added ..." tool_output should be produced.
    """
    base_mod = importlib.import_module("aider.coders.base_coder")

    # First confirm True (run commands), second confirm False (do not add output)
    fake_io = FakeIO(confirm_responses=[True, False])

    class Dummy:
        pass

    inst = Dummy()
    inst.io = fake_io
    inst.root = "/working/dir"

    def run_cmd_stub(cmd, error_print=None, cwd=None):
        # Return some output so that accumulated_output would be non-empty
        return 0, "line1\nline2\n"

    monkeypatch.setattr(base_mod, "run_cmd", run_cmd_stub)

    bound = _bind_handle(base_mod, inst)

    result = bound("echo a\n", group="g2")

    # Since the user declines adding the output, function should return None
    assert result is None

    # Ensure the "Added ..." message is not present in tool outputs
    assert not any((s or "").startswith("Added ") for s in fake_io.tool_outputs)

    # Confirm that add_to_input_history was still called for the executed command
    assert "/run echo a" in fake_io.input_history
