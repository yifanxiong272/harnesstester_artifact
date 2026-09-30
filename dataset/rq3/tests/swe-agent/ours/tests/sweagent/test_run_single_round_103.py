import importlib
import types
from pathlib import Path
import pytest


def _make_config(tmp_path, open_pr=False):
    class Actions:
        def __init__(self, open_pr, apply_patch_locally=False, pr_config=None):
            self.open_pr = open_pr
            self.apply_patch_locally = apply_patch_locally
            self.pr_config = pr_config

    class Config:
        def __init__(self):
            self.env_var_path = tmp_path / "env_file"
            self.output_dir = tmp_path / "out_dir"
            self.agent = "agent-config"
            self.env = "env-config"
            self.problem_statement = "ps"
            self.actions = Actions(open_pr=open_pr, apply_patch_locally=True, pr_config={"repo": "r"})

        def set_default_output_dir(self):
            # no-op for tests
            return None

    return Config()


def test_from_config_without_open_pr_round_103(tmp_path, monkeypatch):
    """
    Verify that when actions.open_pr is False, from_config adds the SaveApplyPatchHook
    and does not add an OpenPRHook. Also verify the agent returned from get_agent_from_config
    receives replay_config assigned.
    """
    run_single = importlib.import_module("sweagent.run.run_single")

    # Patch environment loader to no-op
    monkeypatch.setattr(run_single, "load_environment_variables", lambda path: None)

    # Patch SWEEnv.from_config to deterministic stub
    monkeypatch.setattr(run_single.SWEEnv, "from_config", staticmethod(lambda env: "SWEEnvStub"))

    # Patch get_agent_from_config to return a simple object we can inspect
    class AgentStub:
        pass

    def _get_agent(cfg):
        return AgentStub()

    monkeypatch.setattr(run_single, "get_agent_from_config", _get_agent)

    # Provide stub hook classes that record their constructor args
    created_hooks = []

    class SaveApplyPatchHookStub:
        def __init__(self, apply_patch_locally):
            self.apply_patch_locally = apply_patch_locally
            created_hooks.append(("SaveApplyPatchHook", apply_patch_locally))

    class OpenPRHookStub:
        def __init__(self, pr_config):
            self.pr_config = pr_config
            created_hooks.append(("OpenPRHook", pr_config))

    monkeypatch.setattr(run_single, "SaveApplyPatchHook", SaveApplyPatchHookStub)
    monkeypatch.setattr(run_single, "OpenPRHook", OpenPRHookStub)

    # Replace RunSingle.__init__ to avoid unrelated initialization and to ensure instance has logger
    def dummy_init(self, env, agent, problem_statement, output_dir, actions, hooks=None):
        # simple logger with no side effects
        self.logger = types.SimpleNamespace(debug=lambda *a, **k: created_hooks.append(("debug", a)))
        self.env = env
        self.agent = agent
        self.problem_statement = problem_statement
        self.output_dir = output_dir
        self.actions = actions
        # collector for hooks added by add_hook
        self._added = []

    monkeypatch.setattr(run_single.RunSingle, "__init__", dummy_init)

    # Patch add_hook to append hooks to instance._added so we can assert on them
    def _add_hook(self, hook):
        self._added.append(hook)

    monkeypatch.setattr(run_single.RunSingle, "add_hook", _add_hook)

    cfg = _make_config(tmp_path, open_pr=False)
    inst = run_single.RunSingle.from_config(cfg)

    # The get_agent_from_config stub returns an AgentStub instance; from_config should set replay_config
    assert hasattr(inst.agent, "replay_config"), "agent.replay_config should be set"
    assert inst.agent.replay_config is cfg

    # One SaveApplyPatchHook should have been constructed and added
    assert any(isinstance(h, SaveApplyPatchHookStub) for h in inst._added), "SaveApplyPatchHook was not added"
    # No OpenPRHook should be present when open_pr is False
    assert not any(isinstance(h, OpenPRHookStub) for h in inst._added), "OpenPRHook was unexpectedly added"


def test_from_config_with_open_pr_round_103(tmp_path, monkeypatch):
    """
    Verify that when actions.open_pr is True, from_config logs the addition and adds an OpenPRHook.
    """
    run_single = importlib.import_module("sweagent.run.run_single")

    # Patch environment loader and SWEEnv.from_config
    monkeypatch.setattr(run_single, "load_environment_variables", lambda path: None)
    monkeypatch.setattr(run_single.SWEEnv, "from_config", staticmethod(lambda env: "SWEEnvStub"))

    # Simple agent stub
    class AgentStub:
        pass

    monkeypatch.setattr(run_single, "get_agent_from_config", lambda cfg: AgentStub())

    created_hooks = []

    class SaveApplyPatchHookStub:
        def __init__(self, apply_patch_locally):
            self.apply_patch_locally = apply_patch_locally
            created_hooks.append(("SaveApplyPatchHook", apply_patch_locally))

    class OpenPRHookStub:
        def __init__(self, pr_config):
            self.pr_config = pr_config
            created_hooks.append(("OpenPRHook", pr_config))

    monkeypatch.setattr(run_single, "SaveApplyPatchHook", SaveApplyPatchHookStub)
    monkeypatch.setattr(run_single, "OpenPRHook", OpenPRHookStub)

    # Make __init__ provide a logger that records debug messages
    def dummy_init(self, env, agent, problem_statement, output_dir, actions, hooks=None):
        def _debug(*args, **kwargs):
            # Record debug messages for assertion
            created_hooks.append(("debug", args))

        self.logger = types.SimpleNamespace(debug=_debug)
        self.env = env
        self.agent = agent
        self.problem_statement = problem_statement
        self.output_dir = output_dir
        self.actions = actions
        self._added = []

    monkeypatch.setattr(run_single.RunSingle, "__init__", dummy_init)
    monkeypatch.setattr(run_single.RunSingle, "add_hook", lambda self, hook: self._added.append(hook))

    cfg = _make_config(tmp_path, open_pr=True)
    inst = run_single.RunSingle.from_config(cfg)

    # Should have recorded a debug message indicating OpenPRHook addition
    assert any(entry[0] == "debug" and "Adding OpenPRHook" in entry[1] for entry in created_hooks if entry[0] == "debug" or entry[0] == "debug"), "Logger.debug not called with expected message"

    # Both SaveApplyPatchHook and OpenPRHook should have been instantiated and added
    assert any(isinstance(h, SaveApplyPatchHookStub) for h in inst._added), "SaveApplyPatchHook missing"
    assert any(isinstance(h, OpenPRHookStub) for h in inst._added), "OpenPRHook missing"

    # Confirm OpenPRHook received the pr_config from config.actions
    open_pr_instances = [h for h in inst._added if isinstance(h, OpenPRHookStub)]
    assert open_pr_instances[0].pr_config == cfg.actions.pr_config
