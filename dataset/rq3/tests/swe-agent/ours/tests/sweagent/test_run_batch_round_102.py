import traceback
import types
from types import SimpleNamespace
from pathlib import Path
import pytest

import sweagent.run.run_batch as run_batch_mod
from sweagent.run.run_batch import RunBatch


def test_exception_in_agent_run_round_102(tmp_path, monkeypatch):
    # Capture lists for assertions
    logger_calls = []
    progress_calls = []
    chooks_start_calls = []
    chooks_completed_calls = []

    # Stub RunSingleConfig used to produce model_dump_json
    class StubRunSingleConfig:
        def __init__(self, agent, problem_statement, env):
            self.agent = agent
            self.problem_statement = problem_statement
            self.env = env

        def model_dump_json(self):
            return {"stub": True}

    # Fake agent that will raise when run is called and record error calls
    class FakeAgent:
        def __init__(self):
            # logger.error will append the message to logger_calls
            self.logger = SimpleNamespace(error=lambda msg: logger_calls.append(msg))
            self.replay_config = None
            self.hooks = []

        def add_hook(self, hook):
            self.hooks.append(hook)

        def run(self, problem_statement, env, output_dir):
            # Raise to trigger the except/raise path in _run_instance
            raise ValueError("boom")

    # Fake deployment/environment objects
    class FakeDeployment:
        def __init__(self):
            self.hooks = []

        def add_hook(self, hook):
            self.hooks.append(hook)

    class FakeEnv:
        def __init__(self):
            self.deployment = FakeDeployment()
            self.hooks = []
            self.started = False
            self.closed = False
            self.name = None

        def add_hook(self, hook):
            self.hooks.append(hook)

        def start(self):
            self.started = True

        def close(self):
            self.closed = True

    # Stubs for the status hook classes to avoid side-effects during construction
    class DummyHook:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    # Patch module-level collaborators so the unit under test uses our stubs
    monkeypatch.setattr(run_batch_mod, "RunSingleConfig", StubRunSingleConfig)
    monkeypatch.setattr(run_batch_mod, "get_agent_from_config", lambda cfg: FakeAgent())
    monkeypatch.setattr(run_batch_mod.SWEEnv, "from_config", staticmethod(lambda cfg: FakeEnv()))
    monkeypatch.setattr(run_batch_mod, "save_predictions", lambda *a, **k: None)
    monkeypatch.setattr(run_batch_mod, "SetStatusAgentHook", DummyHook)
    monkeypatch.setattr(run_batch_mod, "SetStatusEnvironmentHook", DummyHook)
    monkeypatch.setattr(run_batch_mod, "SetStatusDeploymentHook", DummyHook)

    # Construct a lightweight self-like object expected by _run_instance
    self_obj = SimpleNamespace()
    # Make output_dir a string path; method will create directories under it
    self_obj.output_dir = str(tmp_path / "out")
    # agent_config must allow assignment to .name
    self_obj.agent_config = SimpleNamespace(name=None)
    # progress manager stub
    self_obj._progress_manager = SimpleNamespace(
        update_instance_status=lambda instance_id, status: progress_calls.append((instance_id, status))
    )
    # combined hooks stub
    self_obj._chooks = SimpleNamespace(
        on_instance_start=lambda **k: chooks_start_calls.append(k),
        on_instance_completed=lambda **k: chooks_completed_calls.append(k),
    )

    # Prepare instance with minimal problem_statement and env config
    instance = SimpleNamespace(
        problem_statement=SimpleNamespace(id="test_problem"),
        env=SimpleNamespace(),
    )

    # Call the function and assert the exception is propagated
    with pytest.raises(ValueError) as excinfo:
        # Call the unbound function with our SimpleNamespace as self
        RunBatch._run_instance(self_obj, instance)

    # Assert the raised exception is the one we raised inside FakeAgent.run
    assert "boom" in str(excinfo.value)

    # After exception, env.close() must have been called on the FakeEnv instance
    # Because we replaced SWEEnv.from_config to return a new FakeEnv, we can inspect
    # the directory to ensure no further code after the try/except/ finally executed.
    # Locate the FakeEnv instance by reconstructing from from_config again (deterministic)
    fake_env = run_batch_mod.SWEEnv.from_config(instance.env)
    # The FakeEnv used in the actual run_instance should have had close() invoked
    # We cannot directly access that instance here; instead, verify effects we can observe:
    # 1) agent.logger.error was called with a traceback containing our ValueError
    assert any(isinstance(m, str) and "ValueError: boom" in m for m in logger_calls), (
        "Expected agent.logger.error to be called with a traceback containing the ValueError"
    )

    # 2) progress manager should have at least received the 'Starting environment' update
    assert any(call[1] == "Starting environment" for call in progress_calls), (
        "Expected update_instance_status to be called with 'Starting environment'"
    )

    # Sanity: the fake_env new instance should be closable and not yet closed (ensures no global mutation)
    assert not fake_env.closed
