import asyncio
import pytest
from sweagent.environment.swe_env import SWEEnv


class DummyResult:
    def __init__(self, output: str, exit_code: int):
        self.output = output
        self.exit_code = exit_code


class DummyLogger:
    def __init__(self):
        self.logged = []
        self.errors = []

    def log(self, level, fmt, *args, **kwargs):
        # emulate formatting used in SWEEnv
        try:
            message = fmt % args if args else fmt
        except Exception:
            message = fmt
        self.logged.append((level, message))

    def error(self, msg: str):
        self.errors.append(msg)


def make_env():
    # Create an instance without running SWEEnv.__init__ and attach the pieces we need
    env = object.__new__(SWEEnv)
    env.logger = DummyLogger()
    # Ensure deployment.runtime.run_in_session exists so the call constructing the coroutine doesn't fail
    env.deployment = type("D", (), {})()
    env.deployment.runtime = type("R", (), {})()
    # Provide a callable so SWEEnv.communicate can call runtime.run_in_session(...) without AttributeError.
    # The actual return value is not used because tests monkeypatch asyncio.run to return DummyResult.
    env.deployment.runtime.run_in_session = lambda action: None

    # close should set a flag we can assert on
    def _close():
        setattr(env, "_closed", True)

    env.close = _close
    return env


def test_communicate_warn_round_058(monkeypatch):
    """When check='warn' and the exit code is non-zero, communicate should log errors but not raise,
    and should return the output. This covers the branch where check != 'ignore' and check == 'warn'.
    """
    env = make_env()

    # Force asyncio.run to return a deterministic result with non-zero exit_code
    monkeypatch.setattr(asyncio, "run", lambda _coro: DummyResult(output="bad output", exit_code=42))

    out = env.communicate("some-cmd", timeout=1, check="warn", error_msg="Oops")

    # It should return the output even though exit_code != 0 (because check == 'warn')
    assert out == "bad output"

    # Two error messages are expected: the first with the error_msg and output, the second the composed msg
    assert len(env.logger.errors) == 2
    assert env.logger.errors[0] == "Oops:\nbad output"
    # The second message must contain the input repr and the r.exit_code formatted as in the code
    assert "Command 'some-cmd' failed (r.exit_code=42): Oops" in env.logger.errors[1]

    # close should not have been called for 'warn'
    assert not getattr(env, "_closed", False)


def test_communicate_raise_round_058(monkeypatch):
    """When check='raise' and the exit code is non-zero, communicate should call close() and raise RuntimeError.
    This covers the branch that raises after logging.
    """
    env = make_env()

    # Provide a deterministic failing result
    monkeypatch.setattr(asyncio, "run", lambda _coro: DummyResult(output="fatal", exit_code=1))

    with pytest.raises(RuntimeError) as excinfo:
        env.communicate("danger", timeout=1, check="raise", error_msg="BOOM")

    # Verify that close() was invoked
    assert getattr(env, "_closed", False) is True

    # Two error messages are expected before raising
    assert len(env.logger.errors) == 2
    assert env.logger.errors[0] == "BOOM:\nfatal"

    # The raised message should match the constructed msg in the source
    expected_msg = "Command 'danger' failed (r.exit_code=1): BOOM"
    assert expected_msg in str(excinfo.value)
