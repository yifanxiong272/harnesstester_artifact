# file: aider/commands.py:356-409
# asked: {"lines": [360, 361, 371, 372, 380, 381, 382, 383, 388, 389, 390, 393, 394, 396, 397, 399, 400, 401, 404, 405, 406, 409], "branches": [[359, 360], [363, 367], [367, 370], [370, 371], [385, 388], [389, 390], [389, 393], [393, 394], [393, 396], [396, 397], [396, 404], [408, 409]]}
# gained: {"lines": [360, 361, 371, 372, 380, 381, 382, 383, 388, 389, 393, 394, 396, 397, 399, 400, 401, 404, 405, 406, 409], "branches": [[359, 360], [370, 371], [385, 388], [389, 393], [393, 394], [396, 397], [408, 409]]}

import pytest

from types import SimpleNamespace
from aider.commands import Commands


class DummyIO:
    def __init__(self, confirm_response=True):
        self.errors = []
        self.warnings = []
        self.outputs = []
        self.confirm_response = confirm_response
        self.confirm_calls = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def confirm_ask(self, prompt, default="y"):
        # Record the prompt for assertions and return preset response
        self.confirm_calls.append((prompt, default))
        return self.confirm_response


class DummyRepo:
    def __init__(self, dirty=False, dirty_files=None):
        self._dirty = dirty
        self._dirty_files = list(dirty_files or [])

    def get_dirty_files(self):
        return list(self._dirty_files)

    def is_dirty(self):
        return self._dirty


class DummyLinter:
    def __init__(self, behavior):
        # behavior is a dict mapping fname -> return value or exception
        self.behavior = behavior

    def lint(self, fname):
        val = self.behavior.get(fname, None)
        if isinstance(val, Exception):
            raise val
        return val


class DummyLintCoder:
    def __init__(self):
        self.added = []
        self.ran_with = []
        self.abs_fnames = set()

    def add_rel_fname(self, fname):
        self.added.append(fname)

    def run(self, errors):
        self.ran_with.append(errors)


class DummyCoder:
    def __init__(
        self,
        repo=None,
        inchat_files=None,
        abs_root_prefix="/abs/",
        linter=None,
        dirty_commits=False,
        auto_commits=False,
    ):
        self.repo = repo
        self._inchat = list(inchat_files or [])
        self.abs_root_prefix = abs_root_prefix
        self.linter = linter
        self.dirty_commits = dirty_commits
        self.auto_commits = auto_commits

        # track clone calls
        self.cloned_with = []

    def get_inchat_relative_files(self):
        return list(self._inchat)

    def abs_root_path(self, fname):
        return self.abs_root_prefix + fname

    def clone(self, **kwargs):
        # record clone args and return a DummyLintCoder
        self.cloned_with.append(kwargs)
        return DummyLintCoder()


def make_cmd(io, coder):
    return Commands(io=io, coder=coder)


def test_cmd_lint_no_repo():
    io = DummyIO()
    coder = DummyCoder(repo=None)
    cmd = make_cmd(io, coder)

    # Run: no repo should produce tool_error and return early
    cmd.cmd_lint("")
    assert io.errors == ["No git repository found."]
    assert io.outputs == []
    assert io.warnings == []


def test_cmd_lint_no_files_warn():
    # repo exists but returns no in-chat files and no dirty files -> warning
    repo = DummyRepo(dirty=False, dirty_files=[])
    linter = DummyLinter({})
    coder = DummyCoder(repo=repo, inchat_files=[], linter=linter)
    io = DummyIO()
    cmd = make_cmd(io, coder)

    cmd.cmd_lint("")
    assert io.warnings == ["No dirty files to lint."]
    assert io.errors == []
    assert io.outputs == []


def test_cmd_lint_file_not_found_and_empty_errors():
    # Setup repo with two dirty files. First raises FileNotFoundError, second returns no errors.
    repo = DummyRepo(dirty=False, dirty_files=["a.py", "b.py"])
    # Note: Commands will convert to abs paths before calling linter
    abs_a = "/abs/a.py"
    abs_b = "/abs/b.py"
    behavior = {
        abs_a: FileNotFoundError("not found a"),
        abs_b: [],  # no errors
    }
    linter = DummyLinter(behavior)
    coder = DummyCoder(repo=repo, inchat_files=[], linter=linter)
    io = DummyIO()
    cmd = make_cmd(io, coder)

    cmd.cmd_lint("")
    # Expect tool_error and tool_output for the FileNotFoundError on first file
    assert any("Unable to lint" in e for e in io.errors)
    assert any("not found a" in o for o in io.outputs)
    # No warnings in this scenario
    assert io.warnings == []


def test_cmd_lint_fixing_errors_commits(monkeypatch):
    # Setup single dirty file with lint errors, confirm True, repo dirty, dirty_commits True, auto_commits True
    repo = DummyRepo(dirty=True, dirty_files=["c.py"])
    abs_c = "/abs/c.py"
    behavior = {abs_c: "SOME ERRORS"}
    linter = DummyLinter(behavior)
    coder = DummyCoder(repo=repo, inchat_files=[], linter=linter, dirty_commits=True, auto_commits=True)
    io = DummyIO(confirm_response=True)
    cmd = make_cmd(io, coder)

    # Patch cmd.cmd_commit to record calls so we don't run the real implementation
    commit_calls = []

    def fake_commit(self_arg, args):
        commit_calls.append(args)

    monkeypatch.setattr(Commands, "cmd_commit", fake_commit, raising=True)

    # Also patch coder.clone to return a DummyLintCoder but still record it (already does)
    # Run the command
    cmd.cmd_lint("")

    # Since repo.is_dirty() True and dirty_commits True, cmd_commit should have been called once before fixes
    # and once at the end because auto_commits True, so total 2 calls
    assert len(commit_calls) == 2
    # verify that clone was called once and that cloned kwargs cleared chat and fnames is None
    assert len(coder.cloned_with) == 1
    clone_kwargs = coder.cloned_with[0]
    assert clone_kwargs.get("cur_messages") == []
    assert clone_kwargs.get("done_messages") == []
    assert clone_kwargs.get("fnames") is None
    # Verify that the DummyLintCoder received the absolute filename and ran with the error string
    # The clone returned a DummyLintCoder instance; we cannot access it directly from coder.cloned_with
    # but we ensure that io.outputs contains the errors string (it is printed before confirm)
    assert any("SOME ERRORS" in str(o) for o in io.outputs)
    # confirm_ask should have been called for the file
    assert io.confirm_calls, "confirm_ask should be called for the file"
    assert "Fix lint errors in /abs/c.py?" in io.confirm_calls[0][0]
