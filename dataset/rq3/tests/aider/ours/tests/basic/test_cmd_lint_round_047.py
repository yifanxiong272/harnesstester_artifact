import types
import builtins
import pytest
from types import SimpleNamespace
from aider import commands

# Helper fakes
class FakeIO:
    def __init__(self, confirm_response=True):
        self.errors = []
        self.warnings = []
        self.outputs = []
        self.confirm_response = confirm_response
        self.confirm_prompts = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def confirm_ask(self, prompt, default="y"):
        # record prompt for assertions and return predetermined response
        self.confirm_prompts.append((prompt, default))
        return self.confirm_response

class FakeRepo:
    def __init__(self, dirty=False, dirty_files=None):
        self._dirty = dirty
        self._dirty_files = dirty_files or []

    def is_dirty(self):
        return self._dirty

    def get_dirty_files(self):
        return list(self._dirty_files)

class FakeLinter:
    def __init__(self, behavior=None):
        # behavior: mapping fname -> either string (errors) or exception instance
        self.behavior = behavior or {}
        self.calls = []

    def lint(self, fname):
        self.calls.append(fname)
        result = self.behavior.get(fname, [])
        if isinstance(result, Exception):
            raise result
        return result

class FakeLintCoder:
    def __init__(self):
        self.added = []
        self.runs = []
        self.abs_fnames = set()

    def add_rel_fname(self, fname):
        self.added.append(fname)

    def run(self, errors):
        self.runs.append(errors)

class FakeCoder:
    def __init__(self, repo=None, linter=None, dirty_commits=False, auto_commits=False):
        self.repo = repo
        self.linter = linter
        self.dirty_commits = dirty_commits
        self.auto_commits = auto_commits
        self._abs_calls = []
        # methods used by cmd_lint
    def get_inchat_relative_files(self):
        return []

    def abs_root_path(self, fname):
        self._abs_calls.append(fname)
        return f"/abs/{fname}"

    def clone(self, **kwargs):
        # Return a new FakeLintCoder for fix operations
        return FakeLintCoder()


# Utility to build a minimal Commands instance without calling its constructor
def make_commands(io, coder):
    cmd = commands.Commands.__new__(commands.Commands)
    cmd.io = io
    cmd.coder = coder
    # Provide a spy for cmd_commit to count calls and record args
    calls = []
    def cmd_commit(arg):
        calls.append(arg)
    cmd.cmd_commit = cmd_commit
    # Keep reference to calls for assertions
    cmd._commit_calls = calls
    return cmd


def test_cmd_lint_no_repo_round_047():
    """If coder.repo is falsy, tool_error is called and method returns early."""
    io = FakeIO()
    coder = SimpleNamespace(repo=None)
    cmd = make_commands(io, coder)

    # Should not raise and should call tool_error once
    result = cmd.cmd_lint(args="")
    assert result is None
    assert io.errors == ["No git repository found."]
    assert io.warnings == []
    assert cmd._commit_calls == []


def test_cmd_lint_no_dirty_files_round_047():
    """No in-chat files and no dirty files in repo triggers a warning and returns."""
    io = FakeIO()
    fake_repo = FakeRepo(dirty=False, dirty_files=[])
    coder = FakeCoder(repo=fake_repo, linter=FakeLinter())
    cmd = make_commands(io, coder)

    # No explicit fnames passed -> will call get_inchat_relative_files (returns [])
    cmd.cmd_lint(args="")
    assert io.warnings == ["No dirty files to lint."]
    assert io.errors == []
    assert cmd._commit_calls == []


def test_cmd_lint_file_not_found_round_047():
    """If linter.lint raises FileNotFoundError, tool_error and tool_output are used and loop continues."""
    io = FakeIO()
    fake_repo = FakeRepo(dirty=False, dirty_files=["fileX.py"])
    behavior = {"file1.py": FileNotFoundError("nope")}
    linter = FakeLinter(behavior=behavior)
    coder = FakeCoder(repo=fake_repo, linter=linter)
    cmd = make_commands(io, coder)

    # Provide fnames explicitly to avoid calling get_inchat_relative_files
    cmd.cmd_lint(args="", fnames=["file1.py"]) 
    # Expect appropriate error and output messages
    assert io.errors == ["Unable to lint file1.py"]
    # tool_output should receive the stringified exception
    assert any("nope" in str(x) for x in io.outputs)
    # No commit or clone activity should happen
    assert cmd._commit_calls == []


def test_cmd_lint_confirm_false_round_047():
    """When lint returns errors and confirm_ask is False, it should not attempt fixes or commits."""
    io = FakeIO(confirm_response=False)
    fake_repo = FakeRepo(dirty=True, dirty_files=["file1.py"])  # dirty but user declines
    linter = FakeLinter(behavior={"file1.py": "SOME LINT ERRORS"})
    coder = FakeCoder(repo=fake_repo, linter=linter, dirty_commits=True, auto_commits=True)
    cmd = make_commands(io, coder)

    cmd.cmd_lint(args="", fnames=["file1.py"]) 
    # It should have output the errors and asked for confirmation
    assert "SOME LINT ERRORS" in io.outputs[0]
    assert len(io.confirm_prompts) == 1
    # Because user declined, no clone/run or commits should have occurred
    assert cmd._commit_calls == []


def test_cmd_lint_fix_and_commit_round_047():
    """Full flow: lint errors, user confirms, pre-commit executed, clone/run invoked, and final auto-commit executed."""
    # io that confirms fixes
    io = FakeIO(confirm_response=True)
    # repo is dirty, dirty_commits True so pre-commit should be triggered
    fake_repo = FakeRepo(dirty=True, dirty_files=["file1.py"]) 
    # linter returns an errors object (truthy)
    linter = FakeLinter(behavior={"file1.py": "ERRORS HERE"})
    coder = FakeCoder(repo=fake_repo, linter=linter, dirty_commits=True, auto_commits=True)

    # We need to ensure coder.clone returns a lint_coder object we can inspect.
    # Patch coder.clone to return a FakeLintCoder instance we control.
    lint_coder = FakeLintCoder()
    def clone_patch(**kwargs):
        # verify the kwargs shape matches expectations: cur_messages, done_messages, fnames
        assert "cur_messages" in kwargs and "done_messages" in kwargs and "fnames" in kwargs
        return lint_coder
    coder.clone = clone_patch

    cmd = make_commands(io, coder)

    cmd.cmd_lint(args="", fnames=["file1.py"]) 

    # Pre-commit should have been called once before fixes
    # and final auto-commit should have been called as well -> total 2
    assert len(cmd._commit_calls) == 2
    # clone produced the lint_coder and its methods should have been used
    assert lint_coder.added == ["/abs/file1.py"] or lint_coder.added == ["file1.py"]
    assert lint_coder.runs == ["ERRORS HERE"]
    # abs_root_path should have been called by coder for the filename
    assert coder._abs_calls == ["file1.py"]
