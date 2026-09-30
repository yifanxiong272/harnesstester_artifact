# file: aider/commands.py:664-695
# asked: {"lines": [666, 667, 671, 672, 677, 680, 681, 686, 687], "branches": [[665, 666], [670, 671], [674, 677], [679, 680], [685, 686]]}
# gained: {"lines": [666, 667, 671, 672, 677, 680, 681, 686, 687], "branches": [[665, 666], [670, 671], [674, 677], [679, 680], [685, 686]]}

import types
import pytest

import aider.commands as commands_mod
from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.outputs = []
        self.printed = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def print(self, msg):
        self.printed.append(msg)


class DummyRepo:
    def __init__(self, head_sha=None, diff_result=""):
        self._head = head_sha
        self.diff_result = diff_result
        self.diff_calls = []

    def get_head_commit_sha(self):
        return self._head

    def diff_commits(self, pretty, before, head):
        # record call for assertions
        self.diff_calls.append((pretty, before, head))
        return self.diff_result


def make_commands_with(coder=None, io=None):
    if io is None:
        io = DummyIO()
    if coder is None:
        coder = types.SimpleNamespace(repo=None, commit_before_message=[], pretty=False)
    # Instantiate Commands with required constructor args
    cmd = Commands(io, coder)
    return cmd, coder, io


def test_raw_cmd_diff_no_repo():
    cmd, coder, io = make_commands_with()
    coder.repo = None

    # Call method
    result = cmd.raw_cmd_diff()

    # Expect tool_error and early return (None)
    assert io.errors == ["No git repository found."]
    assert result is None


def test_raw_cmd_diff_current_head_none():
    repo = DummyRepo(head_sha=None)
    cmd, coder, io = make_commands_with()
    coder.repo = repo
    coder.commit_before_message = []
    coder.pretty = False

    result = cmd.raw_cmd_diff()

    assert io.errors == [
        "Unable to get current commit. The repository might be empty."
    ]
    assert result is None


def test_raw_cmd_diff_commit_before_from_list_and_diff():
    # Setup repo returning a head sha and a diff result
    repo = DummyRepo(head_sha="CURRENTHEAD", diff_result="the-diff-text")
    cmd, coder, io = make_commands_with()
    coder.repo = repo
    # Ensure len >= 2 so commit_before_message is set from [-2]
    coder.commit_before_message = ["commit_before_1", "commit_before_2", "commit_before_3"]
    coder.pretty = False

    result = cmd.raw_cmd_diff()

    # commit_before_message should be the second-last entry
    expected_before = coder.commit_before_message[-2]
    # tool_output should have been called with the short SHA preview
    assert io.outputs == [f"Diff since {expected_before[:7]}..."]
    # repo.diff_commits should have been called exactly once with (pretty, before, HEAD)
    assert repo.diff_calls == [(False, expected_before, "HEAD")]
    # The printed diff should match returned diff_result
    assert io.printed == ["the-diff-text"]
    assert result is None


def test_raw_cmd_diff_commit_before_equals_current_head_triggers_warning():
    # When commit_before_message[-2] == current_head, should warn and return
    repo = DummyRepo(head_sha="SAME_SHA")
    cmd, coder, io = make_commands_with()
    coder.repo = repo
    # Make second-last equal to current head
    # [-2] will be "SAME_SHA"
    coder.commit_before_message = ["SAME_SHA", "something_else"]
    coder.pretty = False

    result = cmd.raw_cmd_diff()

    assert io.warnings == ["No changes to display since the last message."]
    assert result is None


def test_raw_cmd_diff_pretty_true_calls_run_cmd(monkeypatch):
    # Setup repo with a current head
    repo = DummyRepo(head_sha="HEAD123")
    cmd, coder, io = make_commands_with()
    coder.repo = repo
    # Ensure len < 2 so commit_before_message becomes current_head + '^'
    coder.commit_before_message = []
    coder.pretty = True

    called = {}

    def fake_run_cmd(s):
        # record the exact command string called
        called['cmd'] = s
        return "ran"

    # Patch run_cmd in the module where Commands.raw_cmd_diff looks it up
    monkeypatch.setattr(commands_mod, "run_cmd", fake_run_cmd)

    result = cmd.raw_cmd_diff()

    expected_before = repo.get_head_commit_sha() + "^"
    assert called.get("cmd") == f"git diff {expected_before}"
    # When pretty=True, the method returns after run_cmd and should not call repo.diff_commits or io.print
    assert repo.diff_calls == []
    assert io.printed == []
    assert result is None
