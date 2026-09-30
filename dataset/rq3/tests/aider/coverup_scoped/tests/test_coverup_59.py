# file: aider/main.py:101-152
# asked: {"lines": [103, 107, 108, 115, 116, 118, 119, 121], "branches": [[102, 103], [117, 118], [122, 128], [145, 148], [148, 152]]}
# gained: {"lines": [103, 107, 108, 115, 116, 118, 119, 121], "branches": [[102, 103], [117, 118], [122, 128]]}

import builtins
from types import SimpleNamespace
import pathlib
import pytest

import aider.main as am
import aider.repo as ar


class DummyIO:
    def __init__(self, confirm=False):
        self.warnings = []
        self._confirm = confirm
        self.confirm_prompt = None

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def confirm_ask(self, prompt):
        self.confirm_prompt = prompt
        return self._confirm


def test_setup_git_returns_when_git_none(monkeypatch):
    io = DummyIO()
    # Ensure git is None branch executed
    monkeypatch.setattr(am, "git", None)
    res = am.setup_git(None, io)
    assert res is None


def test_setup_git_handles_cwd_oserror(monkeypatch):
    io = DummyIO()
    # Ensure git present so code attempts Path.cwd()
    monkeypatch.setattr(am, "git", SimpleNamespace(Repo=lambda p: None))
    # Make Path.cwd raise OSError
    monkeypatch.setattr(am.Path, "cwd", lambda: (_ for _ in ()).throw(OSError()))
    res = am.setup_git(None, io)
    assert res is None


def test_setup_git_gitrepo_raises_ANY_GIT_ERROR(monkeypatch):
    io = DummyIO()
    # Create git.Repo that raises ANY_GIT_ERROR
    def repo_factory(path):
        raise ar.ANY_GIT_ERROR("failed")
    fake_git = SimpleNamespace(Repo=repo_factory)
    monkeypatch.setattr(am, "git", fake_git)
    # Use some git_root value to exercise that branch
    res = am.setup_git("/nonexistent", io)
    assert res is None


def test_setup_git_home_dir_shows_warning_and_returns(monkeypatch):
    io = DummyIO()
    # Ensure git present
    monkeypatch.setattr(am, "git", SimpleNamespace(Repo=lambda p: None))
    # Make cwd equal to home
    monkeypatch.setattr(am.Path, "cwd", lambda: am.Path.home())
    res = am.setup_git(None, io)
    assert res is None
    assert any("project's directory" in w for w in io.warnings)


def test_setup_git_create_repo_and_set_config_missing_name_email(monkeypatch, tmp_path):
    # This test covers:
    # - confirm_ask True branch creating a new repo via make_new_repo
    # - repo.git.config raising GitCommandError for both name and email
    # - config_writer used to set default name/email and tool_warning called twice
    called = {}

    # Prepare fake io that will confirm creating repo
    io = DummyIO(confirm=True)

    # Patch Path.cwd to return tmp_path
    monkeypatch.setattr(am.Path, "cwd", lambda: tmp_path)

    # Create Dummy GitCommandError class and fake git module with exc
    class DummyGitCommandError(Exception):
        pass

    fake_git = SimpleNamespace()
    fake_git.exc = SimpleNamespace(GitCommandError=DummyGitCommandError)
    # Assign to am.git so the code can refer to fake_git.exc.GitCommandError
    monkeypatch.setattr(am, "git", fake_git)

    # Build fake repo returned by make_new_repo
    class FakeGitConfig:
        def __init__(self):
            self.set_calls = []

        def set_value(self, section, name, value):
            self.set_calls.append((section, name, value))

    class FakeConfigWriter:
        def __enter__(self):
            return fake_git_config

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_git_config = FakeGitConfig()

    class FakeRepo:
        def __init__(self):
            self.working_tree_dir = str(tmp_path.resolve())
            # repo.git.config should raise the DummyGitCommandError for both calls
            self.git = SimpleNamespace(
                config=lambda *args, **kwargs: (_ for _ in ()).throw(DummyGitCommandError())
            )
            self._writer = FakeConfigWriter()

        def config_writer(self):
            return self._writer

    fake_repo = FakeRepo()

    # Patch make_new_repo to return our fake_repo and record git_root argument
    def fake_make_new_repo(git_root, io_arg):
        called["git_root"] = git_root
        called["io"] = io_arg
        return fake_repo

    monkeypatch.setattr(am, "make_new_repo", fake_make_new_repo)

    # Run setup_git with no git_root so it will ask and create via our patched function
    res = am.setup_git(None, io)

    # Assertions: returned path, make_new_repo called with resolved cwd, config set twice, and warnings recorded
    assert res == fake_repo.working_tree_dir
    # git_root passed should be the cwd resolved string
    assert called["git_root"] == str(tmp_path.resolve())
    # Both name and email set
    assert ("user", "name", "Your Name") in fake_git_config.set_calls
    assert ("user", "email", "you@example.com") in fake_git_config.set_calls
    # Two warnings: one for name, one for email
    assert any('git config user.name "Your Name"' in w for w in io.warnings)
    assert any('git config user.email "you@example.com"' in w for w in io.warnings)


def test_setup_git_with_existing_user_config_returns_early(monkeypatch, tmp_path):
    # This test covers the path where repo.git.config returns both name and email
    # so setup_git returns early without writing config.
    io = DummyIO()

    # Prepare fake repo where git.config returns name and email strings
    class FakeRepo:
        def __init__(self):
            self.working_tree_dir = str(tmp_path.resolve())
            self.git = SimpleNamespace(
                config=lambda flag, key: "present" if "user." in key else None
            )
            self.config_writer_called = False

        def config_writer(self):
            self.config_writer_called = True
            class CW:
                def __enter__(self_inner):
                    return self_inner
                def __exit__(self_inner, exc_type, exc, tb):
                    return False
                def set_value(self_inner, a,b,c):
                    pass
            return CW()

    fake_repo = FakeRepo()

    # Patch am.git.Repo to return fake_repo when called with git_root
    def fake_repo_factory(path):
        return fake_repo

    fake_git = SimpleNamespace(Repo=fake_repo_factory)
    monkeypatch.setattr(am, "git", fake_git)

    # Call setup_git with git_root to exercise the git_root->Repo path
    res = am.setup_git(str(tmp_path), io)
    assert res == fake_repo.working_tree_dir
    # Since both user.name and user.email present, config_writer should NOT be used
    assert not fake_repo.config_writer_called
