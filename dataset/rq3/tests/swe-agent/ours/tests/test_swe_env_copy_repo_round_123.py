from sweagent.environment.swe_env import SWEEnv


class DummyRepo:
    def __init__(self, repo_name):
        self.repo_name = repo_name
        self.copied = False
        self.last_deployment = None

    def copy(self, deployment):
        # record invocation so tests can assert on it
        self.copied = True
        self.last_deployment = deployment


class DummyHook:
    def __init__(self):
        self.called = False
        self.last_repo = None

    def on_copy_repo_started(self, repo):
        # record invocation
        self.called = True
        self.last_repo = repo


def _make_env_with_repo(repo):
    # Create SWEEnv instance without invoking its __init__ to avoid external deps
    env = object.__new__(SWEEnv)
    env.repo = repo
    env.deployment = "deployment-xyz"
    env._chook = DummyHook()
    return env


def test_copy_repo_skips_if_present_round_123():
    """When communicate lists the repo name, _copy_repo should return early and not call hooks or copy."""
    repo = DummyRepo("present")
    env = _make_env_with_repo(repo)

    # communicate is expected to be called as self.communicate(input="ls", check="raise")
    # Assign a function that does not accept self (bound as instance attribute)
    env.communicate = lambda input="ls", check="raise": "dir1\npresent\ndir3"

    env._copy_repo()

    # Assertions: copy and hook must NOT have been called
    assert repo.copied is False, "repo.copy should not have been called when repo name is present in folders"
    assert env._chook.called is False, "on_copy_repo_started should not have been called when repo name is present"


def test_copy_repo_triggers_actions_round_123():
    """When communicate does NOT list the repo name, _copy_repo should call the hook and repo.copy with deployment."""
    repo = DummyRepo("missing")
    env = _make_env_with_repo(repo)

    # Return a folder listing that does NOT include the repo name
    env.communicate = lambda input="ls", check="raise": "dir1\nother\ndir3"

    env._copy_repo()

    # Assertions: both hook and repo.copy should have been called with expected args
    assert repo.copied is True, "repo.copy must be called when repo name is not present"
    assert repo.last_deployment == env.deployment, "repo.copy should be called with env.deployment"
    assert env._chook.called is True, "on_copy_repo_started should be called when repo is not present"
    assert env._chook.last_repo is repo, "on_copy_repo_started should receive the repo object"


def test_copy_repo_no_repo_round_123():
    """If env.repo is None, _copy_repo should return immediately and not call communicate or hooks."""
    env = object.__new__(SWEEnv)
    env.repo = None
    env.deployment = "deployment-xyz"

    # If communicate is invoked unexpectedly, fail the test
    def _fail_communicate(*a, **k):
        raise AssertionError("communicate should not be called when repo is None")

    env.communicate = _fail_communicate
    env._chook = DummyHook()

    # Should not raise and should not call hook
    env._copy_repo()
    assert env._chook.called is False, "on_copy_repo_started should not be called when repo is None"
