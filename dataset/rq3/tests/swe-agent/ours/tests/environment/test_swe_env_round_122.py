import importlib
import sys
import types
import pytest

# Prepare lightweight dummy modules for external imports so importing the target module is safe
_dummy = types.ModuleType("_dummy")

# swerex.deployment.abstract
mod = types.ModuleType("swerex.deployment.abstract")
setattr(mod, "AbstractDeployment", object)
sys.modules["swerex.deployment.abstract"] = mod

# swerex.deployment.config
mod = types.ModuleType("swerex.deployment.config")
setattr(mod, "DeploymentConfig", object)
setattr(mod, "DockerDeploymentConfig", object)
setattr(mod, "get_deployment", lambda *a, **k: None)
sys.modules["swerex.deployment.config"] = mod

# swerex.runtime.abstract
mod = types.ModuleType("swerex.runtime.abstract")
# define names that are imported in the module; they can be simple placeholders
for name in (
    "BashAction",
    "BashInterruptAction",
    "CreateBashSessionRequest",
    "ReadFileRequest",
    "WriteFileRequest",
    "Command",
):
    setattr(mod, name, object)
sys.modules["swerex.runtime.abstract"] = mod
sys.modules["swerex.runtime"] = types.ModuleType("swerex.runtime")

# sweagent.environment.hooks.abstract - must provide CombinedEnvHooks and EnvHook
mod = types.ModuleType("sweagent.environment.hooks.abstract")
class _DummyCombined:
    def __init__(self):
        # simple state to help tests validate assignment
        self._created = True
class _DummyHook:
    pass
setattr(mod, "CombinedEnvHooks", _DummyCombined)
setattr(mod, "EnvHook", _DummyHook)
sys.modules["sweagent.environment.hooks.abstract"] = mod

# sweagent.environment.repo - provide Repo and RepoConfig placeholders
mod = types.ModuleType("sweagent.environment.repo")
setattr(mod, "Repo", object)
setattr(mod, "RepoConfig", object)
sys.modules["sweagent.environment.repo"] = mod

# sweagent.utils.log - provide get_logger to avoid side effects
mod = types.ModuleType("sweagent.utils.log")
setattr(mod, "get_logger", lambda *a, **k: (lambda *args, **kwargs: None))
sys.modules["sweagent.utils.log"] = mod

# Now import the module under test
swe_env_mod = importlib.import_module("sweagent.environment.swe_env")
SWEEnv = swe_env_mod.SWEEnv


class DummyCombinedReplacement:
    """Replacement CombinedEnvHooks for test isolation."""
    def __init__(self):
        self.created = True


def test_init_no_hooks_round_122(monkeypatch):
    """If hooks is None, SWEEnv.__init__ should not call add_hook and still set attributes."""
    # spy to capture calls to add_hook
    calls = []
    def spy_add_hook(self, hook):
        calls.append((self, hook))

    # Patch CombinedEnvHooks to a lightweight dummy so creation is safe and observable
    monkeypatch.setattr(swe_env_mod, "CombinedEnvHooks", DummyCombinedReplacement)
    # Patch the class method add_hook to our spy
    monkeypatch.setattr(SWEEnv, "add_hook", spy_add_hook)

    deployment = object()
    repo = None
    cmds = ["echo hi"]

    env = SWEEnv(deployment=deployment, repo=repo, post_startup_commands=cmds)

    # core attribute assignments
    assert env.deployment is deployment
    assert env.repo is None
    assert env._post_startup_commands == cmds
    assert env.post_startup_command_timeout == 500
    assert env.name == "main"
    # clean_multi_line_functions should be a callable (lambda identity in implementation)
    assert callable(env.clean_multi_line_functions)
    # _chook should be instance of our patched CombinedEnvHooks
    assert isinstance(env._chook, DummyCombinedReplacement)
    # ensure add_hook NOT called when hooks is None
    assert calls == []


def test_init_with_hooks_calls_add_hook_round_122(monkeypatch):
    """When hooks are provided, SWEEnv.__init__ must call add_hook for each entry, in order."""
    calls = []
    def spy_add_hook(self, hook):
        # record only the hook value for clarity
        calls.append(hook)

    monkeypatch.setattr(swe_env_mod, "CombinedEnvHooks", DummyCombinedReplacement)
    monkeypatch.setattr(SWEEnv, "add_hook", spy_add_hook)

    h1 = object()
    h2 = object()
    env = SWEEnv(deployment=object(), repo=None, post_startup_commands=[], hooks=[h1, h2], name="custom")

    # add_hook should have been invoked for each provided hook, preserving order
    assert calls == [h1, h2]
    # other assignments respected
    assert env.name == "custom"
    assert isinstance(env._chook, DummyCombinedReplacement)
