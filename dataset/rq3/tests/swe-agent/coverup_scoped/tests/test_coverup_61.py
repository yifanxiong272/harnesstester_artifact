# file: sweagent/environment/swe_env.py:128-133
# asked: {"lines": [132, 133], "branches": []}
# gained: {"lines": [132, 133], "branches": []}

import pytest
from types import MethodType

from sweagent.environment.swe_env import SWEEnv


def make_env():
    # minimal valid SWEEnv construction: deployment can be any object, repo can be None
    return SWEEnv(deployment=object(), repo=None, post_startup_commands=[])


def test_hard_reset_calls_close_then_start():
    env = make_env()
    calls = []

    # Replace instance methods with simple call recorders
    env.close = lambda: calls.append("close")
    env.start = lambda: calls.append("start")

    # Execute hard_reset and verify order of calls
    env.hard_reset()
    assert calls == ["close", "start"], "hard_reset should call close() then start() in order"


def test_hard_reset_propagates_exception_from_close_and_does_not_call_start():
    env = make_env()
    calls = []

    def raising_close():
        raise RuntimeError("close failed")

    env.close = raising_close
    env.start = lambda: calls.append("start")

    with pytest.raises(RuntimeError, match="close failed"):
        env.hard_reset()

    # start should not have been called because close raised
    assert calls == [], "start() must not be called if close() raises an exception"
