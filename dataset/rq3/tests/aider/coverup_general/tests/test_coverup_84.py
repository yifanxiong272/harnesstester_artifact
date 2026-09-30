# file: aider/main.py:101-152
# asked: {"lines": [103, 107, 108, 115, 116, 118, 119, 121], "branches": [[102, 103], [117, 118], [122, 128], [145, 148], [148, 152]]}
# gained: {"lines": [103, 107, 108, 115, 116], "branches": [[102, 103], [122, 128]]}

import types
from pathlib import Path
import pytest

import aider.main as main


class DummyIO:
    def __init__(self, confirm=False):
        self._confirm = confirm
        self.warnings = []

    def confirm_ask(self, prompt):
        # record prompt for debugging if needed
        self.last_prompt = prompt
        return self._confirm

    def tool_warning(self, msg):
        self.warnings.append(msg)


def test_setup_git_returns_when_git_none(monkeypatch):
    # Ensure early return when git module is None
    monkeypatch.setattr(main, "git", None)
    io = DummyIO()
    res = main.setup_git(None, io)
    assert res is None


def test_setup_git_cwd_raises_oserror(monkeypatch):
    # Simulate Path.cwd() raising OSError -> cwd becomes None -> no repo -> return
    class FakePath:
        @staticmethod
        def cwd():
            raise OSError()

        @staticmethod
        def home():
            return Path("/home/user")  # not used in this test

    # Ensure git is some non-None object so the function doesn't return early
    monkeypatch.setattr(main, "git", types.SimpleNamespace())
    monkeypatch.setattr(main, "Path", FakePath)
    io = DummyIO()
    res = main.setup_git(None, io)
    assert res is None


def test_setup_git_gitroot_repo_creation_error(monkeypatch):
    # When a git_root is provided and git.Repo raises ANY_GIT_ERROR, repo remains None -> return
    ANY_GIT_ERROR = main.ANY_GIT_ERROR

    # Provide a fake git module whose Repo raises the ANY_GIT_ERROR
    def fake_repo_constructor(root):
        raise ANY_GIT_ERROR("simulated repo error")

    fake_git = types.SimpleNamespace(Repo=fake_repo_constructor)
    # Provide a cwd that is not the user's home to avoid the home-dir branch
    monkeypatch.setattr(main.Path, "cwd", lambda: Path("/tmp/somewhere"))
    monkeypatch.setattr(main, "git", fake_git)

    io = DummyIO()
    res = main.setup_git("/some/gitroot", io)
    assert res is None


def test_setup_git_creates_repo_and_writes_config(monkeypatch):
    # Simulate user confirming creation of a repo, make_new_repo returns a repo
    # whose git.config raises GitCommandError for both user.name and user.email,
    # so config_writer.set_value is called for both.
    warnings = []

    class IO(DummyIO):
        def __init__(self):
            super().__init__(confirm=True)

        def tool_warning(self, msg):
            super().tool_warning(msg)

    io = IO()

    # Ensure cwd is not home
    monkeypatch.setattr(main.Path, "cwd", lambda: Path("/project/dir"))
    monkeypatch.setattr(main.Path, "home", lambda: Path("/home/user"))

    # Create a fake git.exc.GitCommandError exception class
    class FakeGitCommandError(Exception):
        pass

    # Fake git module with exc.GitCommandError
    fake_git = types.SimpleNamespace()
    fake_git.exc = types.SimpleNamespace(GitCommandError=FakeGitCommandError)

    # Define a fake repo that will be returned by make_new_repo
    class FakeConfigWriter:
        def __init__(self, record):
            self.record = record

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_value(self, section, name, value):
            # record the settings for assertions
            self.record.append((section, name, value))

    class FakeGit:
        def __init__(self):
            # .config() calls should raise the GitCommandError to simulate missing config
            def config_get(*args, **kwargs):
                raise FakeGitCommandError("not set")

            self.config = config_get

    class FakeRepo:
        def __init__(self):
            self.working_tree_dir = "/project/dir"
            self.git = FakeGit()
            self._written = []

        def config_writer(self):
            return FakeConfigWriter(self._written)

    fake_repo = FakeRepo()

    # make_new_repo should return our fake_repo
    monkeypatch.setattr(main, "make_new_repo", lambda root, io_arg: fake_repo)
    monkeypatch.setattr(main, "git", fake_git)

    res = main.setup_git(None, io)

    # Ensure that the returned path is the repo's working_tree_dir
    assert res == fake_repo.working_tree_dir

    # Ensure that two config values were set: user.name and user.email
    assert ("user", "name", "Your Name") in fake_repo._written
    assert ("user", "email", "you@example.com") in fake_repo._written

    # Ensure that two warnings were produced to instruct the user to update name/email
    assert any('git config user.name "Your Name"' in w for w in io.warnings)
    assert any('git config user.email "you@example.com"' in w for w in io.warnings)
