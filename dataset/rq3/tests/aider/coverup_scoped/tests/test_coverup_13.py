# file: aider/coders/base_coder.py:2450-2485
# asked: {"lines": [2451, 2452, 2453, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2463, 2465, 2466, 2467, 2468, 2469, 2471, 2472, 2474, 2475, 2476, 2477, 2479, 2480, 2482, 2483, 2484, 2485], "branches": [[2456, 2463], [2456, 2465], [2466, 2467], [2466, 2479], [2468, 2469], [2468, 2471], [2476, 2466], [2476, 2477], [2479, 0], [2479, 2482]]}
# gained: {"lines": [2451, 2452, 2453, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2463, 2465, 2466, 2467, 2468, 2469, 2471, 2472, 2474, 2475, 2476, 2477, 2479, 2480, 2482, 2483, 2484, 2485], "branches": [[2456, 2463], [2456, 2465], [2466, 2467], [2466, 2479], [2468, 2469], [2468, 2471], [2476, 2466], [2476, 2477], [2479, 0], [2479, 2482]]}

import pytest

from types import SimpleNamespace

# Minimal dummy model to satisfy Coder.__init__ expectations
class DummyModel:
    def __init__(self):
        self.reasoning_tag = None
        self.streaming = True
        self.cache_control = False
        self.weak_model = self
        self.max_chat_history_tokens = 1000
        self.info = {'max_input_tokens': 0}
        self.use_repo_map = False
        self.token_count = 0  # required by ChatSummary

    def commit_message_models(self):
        return []

# Minimal fake IO used to capture interactions and control confirm responses
class FakeIO:
    def __init__(self, confirm_responses=None):
        self.pretty = False
        self.encoding = 'utf-8'
        self.chat_history_file = 'chat_history.md'
        self._confirm_responses = list(confirm_responses or [])
        self.confirm_calls = []
        self.tool_outputs = []
        self.input_history = []
        self.tool_errors = []
        self.tool_warnings = []

    def read_text(self, path):
        return ""

    def confirm_ask(self, prompt, subject=None, explicit_yes_required=False, group=None, allow_never=False):
        # Record the call and return next response if provided, else False
        self.confirm_calls.append((prompt, subject, explicit_yes_required, group, allow_never))
        if self._confirm_responses:
            return self._confirm_responses.pop(0)
        return False

    def tool_output(self, msg=None):
        # tool_output can be called with None to print a blank line; store exactly what was passed
        self.tool_outputs.append(msg)

    def add_to_input_history(self, s):
        self.input_history.append(s)

    def tool_error(self, *args, **kwargs):
        self.tool_errors.append((args, kwargs))

    def tool_warning(self, m):
        self.tool_warnings.append(m)


def _make_coder(fake_io):
    # Import here to ensure tests exercise actual Coder class
    from aider.coders.base_coder import Coder
    return Coder(main_model=DummyModel(), io=fake_io)


def test_handle_shell_commands_decline_run(monkeypatch):
    """
    If the user declines the initial confirmation, no commands should be run and None returned.
    Also verify the prompt is singular for a single command and group is passed through.
    """
    fake_io = FakeIO(confirm_responses=[False])
    coder = _make_coder(fake_io)

    # Patch the run_cmd used inside the base_coder module so any unexpected invocation fails the test.
    import aider.coders.base_coder as base_coder

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("run_cmd was called unexpectedly")

    monkeypatch.setattr(base_coder, "run_cmd", _should_not_be_called)

    res = coder.handle_shell_commands("echo hi\n", group="mygroup")
    assert res is None
    # One confirm call was made
    assert len(fake_io.confirm_calls) == 1
    prompt, subject, explicit_yes_required, group, allow_never = fake_io.confirm_calls[0]
    assert prompt == "Run shell command?"  # singular because exactly one actual command
    assert "echo hi" in subject
    assert group == "mygroup"


def test_handle_shell_commands_run_and_add_output(monkeypatch):
    """
    When the user confirms running commands and confirms adding output,
    run_cmd should be called for each non-comment command, inputs added to history,
    and the accumulated output returned. Also verify plural prompt when multiple commands.
    """
    # First True = run commands, Second True = add output to chat
    fake_io = FakeIO(confirm_responses=[True, True])
    coder = _make_coder(fake_io)

    import aider.coders.base_coder as base_coder
    called = []

    def fake_run_cmd(command, error_print=None, cwd=None):
        # Simulate running the command and returning some output
        called.append((command, cwd))
        # Return consistent output for any command
        return 0, f"result_of_{command.strip()}"

    monkeypatch.setattr(base_coder, "run_cmd", fake_run_cmd)

    # Provide two real commands separated by blank/comment lines to exercise parsing and skipping
    commands_str = "echo one\n# a comment\n\nls -la\n"
    res = coder.handle_shell_commands(commands_str, group="g1")

    # Should return accumulated output string
    assert isinstance(res, str)
    assert "Output from echo one" in res
    assert "result_of_echo one" in res
    assert "Output from ls -la" in res
    assert "result_of_ls -la" in res

    # Both commands should have been run (echo one and ls -la)
    assert any("echo one" in c[0] for c in called)
    assert any("ls -la" in c[0] for c in called)

    # Input history should contain entries for each real command
    assert "/run echo one" in fake_io.input_history
    assert "/run ls -la" in fake_io.input_history

    # First prompt should be plural because two non-comment commands
    assert fake_io.confirm_calls[0][0] == "Run shell commands?"

    # A tool_output call should indicate the added lines (plural)
    assert any((m or "").startswith("Added ") for m in fake_io.tool_outputs)


def test_handle_shell_commands_run_no_output(monkeypatch):
    """
    When commands produce no output, accumulated_output is empty and None should be returned.
    Ensure command is still run and added to input history, but the 'Add command output' prompt is not shown.
    """
    fake_io = FakeIO(confirm_responses=[True])  # confirm running, but no second confirm expected
    coder = _make_coder(fake_io)

    import aider.coders.base_coder as base_coder

    called = []

    def fake_run_cmd_no_output(command, error_print=None, cwd=None):
        called.append(command)
        return 0, ""  # No output for any command

    monkeypatch.setattr(base_coder, "run_cmd", fake_run_cmd_no_output)

    res = coder.handle_shell_commands("  # comment\n\n echo nothing\n", group="grp")
    # Because run_cmd returned no output, nothing should be added and method returns None
    assert res is None

    # run_cmd should have been called for the single real command
    assert any("echo nothing" in c for c in called)

    # Input history should have recorded the run command
    assert "/run echo nothing" in fake_io.input_history

    # There should be only the initial confirmation call (no second 'Add command output' prompt)
    assert len(fake_io.confirm_calls) == 1
    assert fake_io.confirm_calls[0][0] == "Run shell command?"
