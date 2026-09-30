import pytest

from aider import commands
from aider.commands import Commands


class DummyIO:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.outputs = []
        self.prints = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def print(self, msg):
        # mirror real print behavior by storing what would be printed
        self.prints.append(msg)


class DummyRepo:
    def __init__(self, head=None, diff_return=None):
        self._head = head
        self._diff_return = diff_return
        self.diff_calls = []

    def get_head_commit_sha(self):
        return self._head

    def diff_commits(self, pretty, before, after):
        self.diff_calls.append((pretty, before, after))
        return self._diff_return


class DummyCoder:
    def __init__(self, repo, commit_before_message=None, pretty=False):
        # commit_before_message should be a list-like per implementation
        self.repo = repo
        self.commit_before_message = list(commit_before_message or [])
        self.pretty = pretty


def make_commands_with(coder, io=None):
    # Create Commands instance without calling __init__ and attach coder/io
    obj = object.__new__(Commands)
    obj.coder = coder
    obj.io = io or DummyIO()
    return obj


def test_no_repo_round_127():
    """When coder.repo is falsy, should call tool_error and return early."""
    coder = DummyCoder(repo=None, commit_before_message=[])
    io = DummyIO()
    cmd = make_commands_with(coder, io)

    # Call method under test
    result = cmd.raw_cmd_diff()

    # Expect the specific error message and no further side-effects
    assert io.errors == ["No git repository found."], "expected tool_error called for missing repo"
    assert io.warnings == []
    assert io.outputs == []
    assert io.prints == []
    assert result is None


def test_no_head_round_127():
    """When repo.get_head_commit_sha returns None, should report an error and return."""
    repo = DummyRepo(head=None, diff_return=None)
    coder = DummyCoder(repo=repo, commit_before_message=[])
    io = DummyIO()
    cmd = make_commands_with(coder, io)

    cmd.raw_cmd_diff()

    assert io.errors == [
        "Unable to get current commit. The repository might be empty."
    ]
    # no output or print expected
    assert io.outputs == []
    assert io.prints == []


def test_commit_before_message_equal_head_triggers_warning_round_127():
    """If computed commit_before_message equals current head, tool_warning is called and returns."""
    current_head = "deadbeefcafebabe"
    # Make commit_before_message such that [-2] is equal to current_head
    commit_before_message_list = [current_head, "something-else"]
    repo = DummyRepo(head=current_head, diff_return=None)
    coder = DummyCoder(repo=repo, commit_before_message=commit_before_message_list, pretty=False)
    io = DummyIO()
    cmd = make_commands_with(coder, io)

    cmd.raw_cmd_diff()

    assert io.warnings == ["No changes to display since the last message."], "expected warning when commit before equals head"
    assert io.outputs == []
    assert io.prints == []


def test_pretty_true_runs_run_cmd_round_127(monkeypatch):
    """When pretty is True and there are changes, run_cmd is called with git diff and tool_output is emitted."""
    current_head = "0123456789abcdef"
    # commit_before_message length < 2 -> will be computed as current_head + '^'
    repo = DummyRepo(head=current_head, diff_return=None)
    coder = DummyCoder(repo=repo, commit_before_message=[], pretty=True)
    io = DummyIO()
    cmd = make_commands_with(coder, io)

    called = {}

    def fake_run_cmd(arg):
        # record the argument deterministically
        called['arg'] = arg
        return 0

    # Patch run_cmd where the code under test resolves it
    monkeypatch.setattr(commands, 'run_cmd', fake_run_cmd)

    cmd.raw_cmd_diff()

    # commit_before_message should be current_head + '^' per implementation
    expected_before = current_head + "^"
    assert 'arg' in called, "run_cmd should have been called for pretty=True"
    assert called['arg'] == f"git diff {expected_before}"

    # Also the tool_output line should have been emitted with short sha prefix
    assert io.outputs == [f"Diff since {expected_before[:7]}..."], "expected Diff since output"
    # Because pretty branch returns early, no repo.diff_commits calls and no prints
    assert repo.diff_calls == []
    assert io.prints == []


def test_diff_commits_path_round_127():
    """When pretty is False and commit_before_message is chosen from coder.commit_before_message[-2], diff_commits is called and printed."""
    current_head = "feedfacecafef00d"
    # Ensure length >= 2 so commit_before_message uses [-2]
    commit_before_message_list = ["ignore-me", "abc1234before", "later"]
    chosen_before = commit_before_message_list[-2]

    expected_diff = "--- a/file\n+++ b/file\n@@ -1 +1 @@\n-Hello\n+Hello world\n"
    repo = DummyRepo(head=current_head, diff_return=expected_diff)
    coder = DummyCoder(repo=repo, commit_before_message=commit_before_message_list, pretty=False)
    io = DummyIO()
    cmd = make_commands_with(coder, io)

    cmd.raw_cmd_diff()

    # It should have printed the diff returned by repo.diff_commits
    assert repo.diff_calls == [(False, chosen_before, "HEAD")], "diff_commits should be called with (pretty, before, 'HEAD')"
    assert io.prints == [expected_diff]
    # Also should have emitted the tool_output line announcing the diff
    assert io.outputs == [f"Diff since {chosen_before[:7]}..."], "expected Diff since output with short commit"
