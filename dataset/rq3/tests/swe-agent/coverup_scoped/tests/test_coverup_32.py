# file: sweagent/environment/swe_env.py:196-231
# asked: {"lines": [225, 226, 227, 228, 229, 230], "branches": [[224, 225], [228, 229], [228, 231]]}
# gained: {"lines": [225, 226, 227, 228, 229, 230], "branches": [[224, 225], [228, 229], [228, 231]]}

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from sweagent.environment.swe_env import SWEEnv


class DummyRuntime:
    def __init__(self):
        # run_in_session won't actually be awaited because we monkeypatch asyncio.run
        self.run_in_session = lambda action: "ignored-coroutine"


class DummyDeployment:
    def __init__(self):
        self.runtime = DummyRuntime()


def make_env():
    return SWEEnv(deployment=DummyDeployment(), repo=None, post_startup_commands=[])


def _set_asyncio_run(monkeypatch, result_obj):
    """Replace asyncio.run with a function that returns result_obj regardless of input."""
    monkeypatch.setattr(asyncio, "run", lambda coro: result_obj)


def _assert_logger_errors_called(mock_logger, first_msg, second_msg):
    # logger.error is expected to be called twice with the two messages
    assert mock_logger.error.call_count == 2
    calls = [call.args for call in mock_logger.error.call_args_list]
    assert calls[0] == (first_msg,)
    assert calls[1] == (second_msg,)


def test_communicate_warn_logs_but_does_not_raise(monkeypatch):
    # Prepare stubbed result with non-zero exit_code to trigger logging branch
    stub = SimpleNamespace(output="something went wrong\n", exit_code=7)

    # Create environment
    env = make_env()

    # Replace asyncio.run to return our stub
    _set_asyncio_run(monkeypatch, stub)

    # Replace logger with MagicMock to capture error/log calls
    mock_logger = MagicMock()
    env.logger = mock_logger

    # Call communicate with check="warn" which should log errors but not raise
    result = env.communicate("echo fail", timeout=1, check="warn", error_msg="Boom!")

    # Ensure output returned unchanged
    assert result == stub.output

    # Check that two error logs were emitted with the expected contents
    first_expected = f"Boom!:\n{stub.output}"
    second_expected = f"Command {'echo fail'!r} failed (r.exit_code={stub.exit_code}): Boom!"
    _assert_logger_errors_called(mock_logger, first_expected, second_expected)


def test_communicate_raise_calls_close_and_raises(monkeypatch):
    # Prepare stubbed result with non-zero exit_code to trigger raise branch
    stub = SimpleNamespace(output="critical failure", exit_code=42)

    # Create environment
    env = make_env()

    # Replace asyncio.run to return our stub
    _set_asyncio_run(monkeypatch, stub)

    # Replace logger with MagicMock to capture error/log calls
    mock_logger = MagicMock()
    env.logger = mock_logger

    # Monkeypatch/spy on close to ensure it is called
    env.close = MagicMock(name="close")

    # Call communicate with check="raise" which should call close and then raise RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        env.communicate("do something", timeout=1, check="raise", error_msg="Fatal")

    # Verify close was called exactly once
    env.close.assert_called_once()

    # Verify exception message is as expected
    expected_msg = f"Command {'do something'!r} failed (r.exit_code={stub.exit_code}): Fatal"
    assert str(excinfo.value) == expected_msg

    # Also verify the two error log calls occurred
    first_expected = f"Fatal:\n{stub.output}"
    _assert_logger_errors_called(mock_logger, first_expected, expected_msg)
