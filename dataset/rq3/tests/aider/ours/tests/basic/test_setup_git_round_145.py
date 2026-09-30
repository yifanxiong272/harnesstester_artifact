import types
import pytest

from aider import main as aider_main
from aider.main import setup_git


class DummyIO:
    def __init__(self, confirm=False):
        self.warnings = []
        self._confirm = confirm

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def confirm_ask(self, msg):
        # deterministic: return configured boolean
        return self._confirm


def test_setup_git_git_none_round_145():
    """If module-level git is None, setup_git should return immediately (line 102->103).
    """
    # Arrange: patch module git to None
    original_git = aider_main.git
    aider_main.git = None
    io = DummyIO()

    try:
        # Act
        result = setup_git("/irrelevant", io)
        # Assert
        assert result is None
    finally:
        # Teardown
        aider_main.git = original_git


def test_setup_git_path_cwd_raises_round_145(monkeypatch):
    """Simulate Path.cwd raising OSError so cwd becomes None (lines 106-108) and
    simulate git.Repo raising ANY_GIT_ERROR when git_root provided (lines 113-116).
    The function should return None because repo remains falsy.
    """
    # Arrange
    class MyRepoError(Exception):
        pass

    # Make git.Repo raise our error
    fake_git = types.SimpleNamespace()

    def fake_repo_constructor(path):
        raise MyRepoError("no repo")

    fake_git.Repo = fake_repo_constructor
    # Ensure git.exc.GitCommandError exists but not used here
    fake_git.exc = types.SimpleNamespace(GitCommandError=Exception)

    monkeypatch.setattr(aider_main, "git", fake_git)
    # Ensure ANY_GIT_ERROR will match MyRepoError
    monkeypatch.setattr(aider_main, "ANY_GIT_ERROR", MyRepoError)

    # Patch Path.cwd to raise OSError
    class DummyPath:
        @staticmethod
        def cwd():
            raise OSError("cant access cwd")

    monkeypatch.setattr(aider_main, "Path", DummyPath)

    io = DummyIO()

    # Act
    result = setup_git("/some/root", io)

    # Assert: repo could not be created -> returns None
    assert result is None


def test_setup_git_home_dir_warning_round_145(monkeypatch):
    """When cwd equals home and no git_root is provided, should warn and return (lines 117-121).
    """
    # Arrange: create dummy path object to be returned by both cwd() and home()
    class DummyHome:
        def resolve(self):
            return "/home/user"

        def __eq__(self, other):
            # equality to emulate Path objects comparison
            return isinstance(other, DummyHome) or (hasattr(other, "resolve") and other.resolve() == "/home/user")

    dummy = DummyHome()

    class DummyPath:
        @staticmethod
        def cwd():
            return dummy

        @staticmethod
        def home():
            return dummy

    monkeypatch.setattr(aider_main, "Path", DummyPath)

    # Provide a git object that would not be used; keep simple stub
    monkeypatch.setattr(aider_main, "git", types.SimpleNamespace())

    io = DummyIO()

    # Act
    result = setup_git(None, io)

    # Assert: a warning was emitted and function returned None
    assert result is None
    assert any("project's directory" in w or "home dir" in w or "project" in w for w in io.warnings)


def test_setup_git_create_repo_and_config_present_round_145(monkeypatch):
    """Simulate creating a new repo via make_new_repo and repo already has user.name and user.email
    so setup_git returns working_tree_dir (lines 122-142).
    """
    # Arrange: cwd is some project dir different from home
    class DummyCwd:
        def resolve(self):
            return "/project/path"

        def __eq__(self, other):
            return False

    class DummyPath:
        @staticmethod
        def cwd():
            return DummyCwd()

        @staticmethod
        def home():
            return object()  # different

    monkeypatch.setattr(aider_main, "Path", DummyPath)

    # io that agrees to create a repo
    io = DummyIO(confirm=True)

    # Create a repo-like object that has git.config and working_tree_dir
    class FakeGitConfig:
        def __init__(self):
            pass

    class FakeRepo:
        def __init__(self):
            self.working_tree_dir = "/repo/working"
            # git.config should accept --get user.name/email
            self.git = types.SimpleNamespace()

            def cfg(option, key):
                if key == "user.name":
                    return "Alice"
                if key == "user.email":
                    return "alice@example.com"
                return ""

            self.git.config = cfg

        def config_writer(self):
            # Not used in this test because both name and email exist
            raise AssertionError("config_writer should not be used when both name and email are present")

    fake_repo = FakeRepo()

    # Patch make_new_repo to return our fake_repo
    monkeypatch.setattr(aider_main, "make_new_repo", lambda git_root, io_arg: fake_repo)

    # Patch git to a stub so earlier checks (git is not None) pass
    monkeypatch.setattr(aider_main, "git", types.SimpleNamespace(exc=types.SimpleNamespace(GitCommandError=Exception)))

    # Act
    result = setup_git(None, io)

    # Assert
    assert result == "/repo/working"


def test_setup_git_set_config_when_missing_round_145(monkeypatch):
    """When repo config has no user.name and no user.email, setup_git should call
    repo.config_writer.set_value for both name and email and warn via io.tool_warning
    (lines 144-151) and then return working_tree_dir.
    """
    # Arrange: cwd is some project dir different from home and confirm_ask True so make_new_repo used
    class DummyCwd:
        def resolve(self):
            return "/other/project"

        def __eq__(self, other):
            return False

    class DummyPath:
        @staticmethod
        def cwd():
            return DummyCwd()

        @staticmethod
        def home():
            return object()

    monkeypatch.setattr(aider_main, "Path", DummyPath)

    io = DummyIO(confirm=True)

    # Build fake repo where git.config returns empty values -> triggers setting in config_writer
    class FakeConfigWriter:
        def __init__(self):
            self.calls = []

        def set_value(self, section, name, value):
            self.calls.append((section, name, value))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeRepo2:
        def __init__(self):
            self.working_tree_dir = "/repo/with/config"
            self.git = types.SimpleNamespace()

            def cfg(option, key):
                # Always return empty so user_name and user_email are falsy
                return ""

            self.git.config = cfg

        def config_writer(self):
            return FakeConfigWriter()

    fake_repo = FakeRepo2()

    monkeypatch.setattr(aider_main, "make_new_repo", lambda git_root, io_arg: fake_repo)
    monkeypatch.setattr(aider_main, "git", types.SimpleNamespace(exc=types.SimpleNamespace(GitCommandError=Exception)))

    # Act
    result = setup_git(None, io)

    # Assert: returns working tree dir and emitted two warnings and config_writer had set_value calls
    assert result == "/repo/with/config"
    # two tool warnings expected for name and email
    assert any("git name" in w or "user.name" in w or "Update git name" in w for w in io.warnings)
    assert any("git email" in w or "user.email" in w or "Update git email" in w for w in io.warnings)
