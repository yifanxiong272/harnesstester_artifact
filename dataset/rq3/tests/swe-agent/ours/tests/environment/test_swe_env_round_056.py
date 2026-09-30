import types
import pytest
from sweagent.environment import swe_env
from sweagent.environment.swe_env import SWEEnv


class DummyLogger:
    def __init__(self):
        self.logged = []
        self.errors = []

    def log(self, *args, **kwargs):
        # record trace/log calls for inspection if needed
        self.logged.append((args, kwargs))

    def error(self, msg):
        # record error messages for assertions
        self.errors.append(msg)


class DummyRuntime:
    def __init__(self, result_holder):
        self.result_holder = result_holder
        self.last_action = None

    def run_in_session(self, action):
        # capture the action object for potential inspection
        self.last_action = action
        # return the pre-built result object (asyncio.run will be patched to identity)
        return self.result_holder


def make_env(result_obj):
    # create SWEEnv without calling its real __init__ and inject required attributes
    env = object.__new__(SWEEnv)
    env.logger = DummyLogger()
    env.deployment = types.SimpleNamespace(runtime=DummyRuntime(result_obj))
    env.close_called = False

    def _close():
        env.close_called = True

    env.close = _close
    return env


def test_warn_nonzero_exit_round_056(monkeypatch):
    """When check='warn' and exit_code != 0, communicate should return output and log errors but not raise or close."""
    # Patch asyncio.run in the module under test to be identity (no real event loop)
    monkeypatch.setattr(swe_env.asyncio, "run", lambda x: x)

    result = types.SimpleNamespace(output="something failed", exit_code=2)
    env = make_env(result)

    out = env.communicate("my-cmd", check="warn")

    assert out == "something failed"
    # Two error logs should have been emitted per the code path: first error with output, then the composed msg
    assert len(env.logger.errors) >= 2
    assert env.logger.errors[0] == "Command failed:\nsomething failed"
    # second message contains the failing command and exit code information
    assert "Command 'my-cmd' failed (r.exit_code=2): Command failed" in env.logger.errors[1]
    # close should not have been called for 'warn'
    assert env.close_called is False


def test_raise_nonzero_exit_round_056(monkeypatch):
    """When check='raise' and exit_code != 0, communicate should call close() and raise RuntimeError with expected message."""
    monkeypatch.setattr(swe_env.asyncio, "run", lambda x: x)

    result = types.SimpleNamespace(output="badness", exit_code=3)
    env = make_env(result)

    with pytest.raises(RuntimeError) as exc:
        env.communicate("run-me", check="raise")

    # close must have been invoked before raising
    assert env.close_called is True
    # runtime error text should include the constructed message
    assert "Command 'run-me' failed (r.exit_code=3): Command failed" in str(exc.value)


def test_ignore_no_error_round_056(monkeypatch):
    """When check='ignore' the method should not log errors or raise even if exit_code != 0."""
    monkeypatch.setattr(swe_env.asyncio, "run", lambda x: x)

    result = types.SimpleNamespace(output="ignored-out", exit_code=9)
    env = make_env(result)

    out = env.communicate("noop", check="ignore")

    assert out == "ignored-out"
    # no error logging when check == 'ignore'
    assert env.logger.errors == []
    assert env.close_called is False
