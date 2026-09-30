import importlib
from pathlib import Path
import yaml
import pytest

run_single = importlib.import_module("sweagent.run.run_single")
RunSingle = run_single.RunSingle


class DummyHooks:
    def __init__(self):
        self.calls = []

    def on_init(self, run):
        # record that on_init was called with the RunSingle instance
        self.calls.append(("on_init", type(run).__name__))

    def on_start(self):
        self.calls.append("on_start")

    def on_instance_start(self, **kwargs):
        # record the received keyword keys
        self.calls.append(("on_instance_start", set(kwargs.keys())))

    def on_instance_completed(self, *, result):
        self.calls.append(("on_instance_completed", result))

    def on_end(self):
        self.calls.append("on_end")


class DummyEnv:
    def __init__(self):
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def close(self):
        self.closed = True


class DummyProblemStatement:
    def __init__(self, id_):
        self.id = id_


class DummyReplayConfig:
    def __init__(self, payload):
        self._payload = payload

    def model_dump_json(self):
        return self._payload


class DummyAgent:
    def __init__(self, replay_config, run_result=None):
        self.replay_config = replay_config
        self._run_result = run_result if run_result is not None else {"ok": True}
        self.run_called_with = None

    def run(self, *, problem_statement, env, output_dir):
        self.run_called_with = {
            "problem_statement_id": getattr(problem_statement, "id", None),
            "env_started": getattr(env, "started", None),
            "output_dir": str(output_dir),
        }
        return self._run_result


class DummyCombinedHooks:
    """A minimal CombinedRunHooks replacement matching the contract used by RunSingle.

    RunSingle calls CombinedRunHooks() without args. It expects the returned
    object to have add_hook(hook) plus lifecycle methods on_start, on_instance_start,
    on_instance_completed, on_end which should dispatch to contained hooks.
    """

    def __init__(self):
        self._hooks = []

    def add_hook(self, hook):
        self._hooks.append(hook)

    def on_start(self):
        for h in self._hooks:
            h.on_start()

    def on_instance_start(self, **kwargs):
        for h in self._hooks:
            h.on_instance_start(**kwargs)

    def on_instance_completed(self, *, result):
        for h in self._hooks:
            h.on_instance_completed(result=result)

    def on_end(self):
        for h in self._hooks:
            h.on_end()


def _patch_combined_hooks_and_save(monkeypatch, record):
    # Ensure CombinedRunHooks can be constructed without args and dispatches to provided hooks
    monkeypatch.setattr(run_single, "CombinedRunHooks", lambda: DummyCombinedHooks())

    def fake_save_predictions(output_dir, problem_id, result):
        # record strings for determinism
        record.append((str(output_dir), problem_id, result))

    monkeypatch.setattr(run_single, "save_predictions", fake_save_predictions)


def test_run_with_replay_config_round_147(tmp_path, monkeypatch):
    """Covers branch where agent.replay_config is not None and config.yaml is written."""
    records = []
    _patch_combined_hooks_and_save(monkeypatch, records)

    hooks = DummyHooks()
    env = DummyEnv()
    problem = DummyProblemStatement("prob-123")
    base_output = tmp_path

    payload = {"model": "test-model", "param": 42}
    replay_config = DummyReplayConfig(payload)

    agent = DummyAgent(replay_config=replay_config, run_result={"status": "done"})

    rs = RunSingle(env=env, agent=agent, problem_statement=problem, output_dir=base_output, hooks=[hooks], actions=None)
    rs.run()

    # Env lifecycle
    assert env.started is True
    assert env.closed is True

    # Hooks: on_init should have been called (via add_hook) and lifecycle calls dispatched
    assert any(isinstance(c, tuple) and c[0] == "on_init" for c in hooks.calls)
    # on_start must have been called
    assert "on_start" in hooks.calls
    # instance_start should include 'env' and 'problem_statement'
    assert any(c[0] == "on_instance_start" and "env" in c[1] and "problem_statement" in c[1] for c in hooks.calls)
    # instance_completed must have been called with agent.run result
    assert any(c[0] == "on_instance_completed" and c[1] == {"status": "done"} for c in hooks.calls)
    # on_end finalizer present
    assert hooks.calls[-1] == "on_end"

    # config.yaml file must exist under output_dir/problem.id
    expected_file = base_output / problem.id / "config.yaml"
    assert expected_file.exists(), f"expected config file at {expected_file}"

    content = expected_file.read_text()
    # YAML should contain payload keys/values
    assert "model" in content
    assert "param: 42" in content

    # Agent.run called with problem id and save_predictions recorded the result
    assert agent.run_called_with["problem_statement_id"] == problem.id
    assert records == [(str(base_output), problem.id, {"status": "done"})]


def test_run_without_replay_config_round_147(tmp_path, monkeypatch):
    """Covers path where agent.replay_config is None and no config.yaml is created."""
    records = []
    _patch_combined_hooks_and_save(monkeypatch, records)

    hooks = DummyHooks()
    env = DummyEnv()
    problem = DummyProblemStatement("no-config")
    base_output = tmp_path

    agent = DummyAgent(replay_config=None, run_result={"status": "no-config"})

    rs = RunSingle(env=env, agent=agent, problem_statement=problem, output_dir=base_output, hooks=[hooks], actions=None)
    rs.run()

    expected_file = base_output / problem.id / "config.yaml"
    assert not expected_file.exists(), "config.yaml should not be created when agent.replay_config is None"

    assert records == [(str(base_output), problem.id, {"status": "no-config"})]
    assert env.started is True and env.closed is True
    assert any(isinstance(c, tuple) and c[0] == "on_init" for c in hooks.calls)
    assert hooks.calls[-1] == "on_end"
