# file: sweagent/environment/swe_env.py:52-82
# asked: {"lines": [82], "branches": [[81, 82]]}
# gained: {"lines": [82], "branches": [[81, 82]]}

import builtins
import types

import pytest

from sweagent.environment import swe_env as swe_env_module
from sweagent.environment.hooks.abstract import EnvHook


class DummyDeployment:
    pass


class FakeCombinedEnvHooks:
    def __init__(self):
        self._hooks = []
        self.add_calls = []

    def add_hook(self, hook: EnvHook) -> None:
        self.add_calls.append(hook)
        self._hooks.append(hook)


def test_init_with_hooks_calls_add_hook_and_on_init(monkeypatch):
    # Arrange: replace CombinedEnvHooks in the swe_env module with a fake that records add_hook calls
    monkeypatch.setattr(swe_env_module, "CombinedEnvHooks", FakeCombinedEnvHooks)

    called = {}

    class MyHook(EnvHook):
        def on_init(self, *, env):
            # record that on_init was called and the env object
            called["env"] = env

    hook = MyHook()

    # Act: create SWEEnv with one hook; this should call add_hook(hook) inside __init__
    env = swe_env_module.SWEEnv(
        deployment=DummyDeployment(),
        repo=None,
        post_startup_commands=[],
        hooks=[hook],
    )

    # Assert: on_init was called with the created env
    assert "env" in called and called["env"] is env

    # Assert: the CombinedEnvHooks instance attached to env recorded the hook via add_hook
    assert isinstance(env._chook, FakeCombinedEnvHooks)
    assert hook in env._chook._hooks
    assert env._chook.add_calls == [hook]

    # Also verify some basic properties set by __init__
    assert env.deployment.__class__ is DummyDeployment
    assert env.repo is None
    assert env.name == "main"


def test_init_with_no_hooks_does_not_call_on_init(monkeypatch):
    # Arrange: replace CombinedEnvHooks again to avoid side effects
    monkeypatch.setattr(swe_env_module, "CombinedEnvHooks", FakeCombinedEnvHooks)

    class BadHook(EnvHook):
        def on_init(self, *, env):
            raise AssertionError("on_init should not be called when hooks is None")

    # Act: creating SWEEnv with hooks=None should not attempt to add any hooks
    env = swe_env_module.SWEEnv(
        deployment=DummyDeployment(),
        repo=None,
        post_startup_commands=[],
        hooks=None,
    )

    # Assert: CombinedEnvHooks was created but no hooks present
    assert isinstance(env._chook, FakeCombinedEnvHooks)
    assert env._chook._hooks == []
    # Ensure that other properties exist as expected
    assert hasattr(env, "logger")
    assert env._post_startup_commands == []
    assert env.post_startup_command_timeout == 500
