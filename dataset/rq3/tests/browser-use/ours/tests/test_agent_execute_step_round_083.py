import asyncio
import inspect
from types import SimpleNamespace
import pytest

from browser_use.agent import service as svc

# Helpers used across tests
class DummyLogger:
    def __init__(self):
        self.calls = []

    def debug(self, *args, **kwargs):
        self.calls.append(("debug", args, kwargs))

    def error(self, *args, **kwargs):
        self.calls.append(("error", args, kwargs))


class DummySettings:
    def __init__(self, step_timeout=0.01, use_judge=False):
        self.step_timeout = step_timeout
        self.use_judge = use_judge


class DummyState:
    def __init__(self, n_steps=0):
        self.consecutive_failures = 0
        self.last_result = None
        self.n_steps = n_steps


class DummyHistory:
    def __init__(self, done=False):
        self._done = done

    def is_done(self):
        return self._done


@pytest.mark.asyncio
async def test_timeout_with_on_step_hooks_and_increment_n_steps_round_083(monkeypatch):
    """
    Simulate a TimeoutError from asyncio.wait_for while providing on_step_start and on_step_end
    to trigger the hook calls and the timeout handling branch. Also set state.n_steps == step+1
    to exercise the n_steps increment branch.
    """
    svc_mod = svc

    # Prepare fake self object with the attributes and methods the function expects
    calls = {
        "demo_logs": [],
        "judge_called": False,
        "log_completion_called": False,
        "on_start_called": False,
        "on_end_called": False,
    }

    async def fake_demo_mode_log(message, level, metadata=None):
        calls["demo_logs"].append((message, level, metadata))

    async def fake_judge_and_log():
        calls["judge_called"] = True

    async def fake_log_completion():
        calls["log_completion_called"] = True

    async def on_step_start(self_ref):
        # Verify the object passed is our fake self
        calls["on_start_called"] = True

    async def on_step_end(self_ref):
        calls["on_end_called"] = True

    # Force asyncio.wait_for to raise TimeoutError to exercise the timeout handler
    async def raise_timeout(coro, timeout=None):
        raise TimeoutError()

    monkeypatch.setattr(svc_mod.asyncio, "wait_for", raise_timeout)

    fake_self = SimpleNamespace()
    fake_self._demo_mode_log = fake_demo_mode_log
    fake_self._judge_and_log = fake_judge_and_log
    fake_self.log_completion = fake_log_completion
    fake_self.logger = DummyLogger()
    fake_self.settings = DummySettings(step_timeout=0.001, use_judge=False)
    fake_self.state = DummyState(n_steps=3)
    # choose step such that n_steps == step + 1 triggers increment
    step = 2
    fake_self.state.n_steps = step + 1
    fake_self.history = DummyHistory(done=False)
    # The step implementation won't be awaited because wait_for raises, but provide one anyway
    async def step_impl(step_info):
        # would normally perform work
        return "ok"
    fake_self.step = step_impl

    # Execute
    result = await svc_mod.Agent._execute_step(
        fake_self,
        step=step,
        max_steps=10,
        step_info=None,
        on_step_start=on_step_start,
        on_step_end=on_step_end,
    )

    # Assertions verifying timeout branch behavior
    # Function should return False because history.is_done() is False
    assert result is False

    # Timeout should have incremented consecutive_failures and set last_result
    assert fake_self.state.consecutive_failures == 1
    assert isinstance(fake_self.state.last_result, list)
    # ActionResult shape is preserved: error attribute should be present on the first item
    assert hasattr(fake_self.state.last_result[0], "error")
    assert "timed out" in fake_self.state.last_result[0].error

    # n_steps should have been incremented from step + 1 to step + 2
    assert fake_self.state.n_steps == (step + 2)

    # Hooks should have been called
    assert calls["on_start_called"] is True
    assert calls["on_end_called"] is True

    # Demo mode log should have been called at least for the starting and error messages
    demo_msgs = [m for (m, level, meta) in calls["demo_logs"]]
    assert any("Starting step" in m for m in demo_msgs)
    assert any("timed out" in m for m in demo_msgs)

    # Logger should have at least one debug and one error call recorded
    levels = [c[0] for c in fake_self.logger.calls]
    assert "error" in levels
    assert "debug" in levels


@pytest.mark.asyncio
async def test_history_done_calls_judge_and_register_done_sync_round_083(monkeypatch):
    """
    Simulate a successful step (no timeout) and history.is_done() == True to trigger log_completion,
    the use_judge == True branch where _judge_and_log is called, and a synchronous register_done_callback.
    This covers the branch where register_done_callback is a normal function (non-coroutine).
    """
    svc_mod = svc

    calls = {"demo_logs": [], "judge_called": False, "log_completion_called": False, "register_called_with": None}

    async def fake_demo_mode_log(message, level, metadata=None):
        calls["demo_logs"].append((message, level, metadata))

    async def fake_judge_and_log():
        calls["judge_called"] = True

    async def fake_log_completion():
        calls["log_completion_called"] = True

    # Make asyncio.wait_for behave like the real awaiter: await the coroutine and return its result
    async def passthrough_wait_for(coro, timeout=None):
        return await coro

    monkeypatch.setattr(svc_mod.asyncio, "wait_for", passthrough_wait_for)

    fake_self = SimpleNamespace()
    fake_self._demo_mode_log = fake_demo_mode_log
    fake_self._judge_and_log = fake_judge_and_log
    fake_self.log_completion = fake_log_completion
    fake_self.logger = DummyLogger()
    fake_self.settings = DummySettings(step_timeout=1.0, use_judge=True)
    fake_self.state = DummyState(n_steps=0)

    # history.is_done True to reach the done branch
    fake_self.history = DummyHistory(done=True)

    # step implementation completes normally
    async def step_impl(step_info):
        return "completed"
    fake_self.step = step_impl

    # synchronous register_done_callback should be called directly (non-async path)
    def register_done(history_obj):
        calls["register_called_with"] = history_obj

    fake_self.register_done_callback = register_done

    # Call without on_step_start to exercise that branch
    result = await svc_mod.Agent._execute_step(
        fake_self,
        step=0,
        max_steps=1,
        step_info=None,
        on_step_start=None,
        on_step_end=None,
    )

    # Should return True because history.is_done() is True
    assert result is True

    # Judge should have been called since use_judge is True
    assert calls["judge_called"] is True

    # log_completion should have been awaited
    assert calls["log_completion_called"] is True

    # The synchronous register_done_callback should have been invoked with the history object
    assert calls["register_called_with"] is fake_self.history


@pytest.mark.asyncio
async def test_history_done_calls_register_done_async_and_skips_judge_round_083(monkeypatch):
    """
    Simulate a successful step with history.is_done() == True and use_judge == False to exercise the
    branch that skips judge. Provide an async register_done_callback to cover the coroutine-callback path.
    """
    svc_mod = svc

    calls = {"register_called_with": None, "judge_called": False, "log_completion_called": False}

    async def fake_demo_mode_log(message, level, metadata=None):
        pass

    async def fake_judge_and_log():
        calls["judge_called"] = True

    async def fake_log_completion():
        calls["log_completion_called"] = True

    async def passthrough_wait_for(coro, timeout=None):
        return await coro

    monkeypatch.setattr(svc_mod.asyncio, "wait_for", passthrough_wait_for)

    fake_self = SimpleNamespace()
    fake_self._demo_mode_log = fake_demo_mode_log
    fake_self._judge_and_log = fake_judge_and_log
    fake_self.log_completion = fake_log_completion
    fake_self.logger = DummyLogger()
    # use_judge=False to follow the branch that does not call judge
    fake_self.settings = DummySettings(step_timeout=1.0, use_judge=False)
    fake_self.state = DummyState(n_steps=0)
    fake_self.history = DummyHistory(done=True)

    async def step_impl(step_info):
        return "ok"
    fake_self.step = step_impl

    async def async_register_done(history_obj):
        calls["register_called_with"] = history_obj

    fake_self.register_done_callback = async_register_done

    # Call with on_step_start None and on_step_end None
    result = await svc_mod.Agent._execute_step(
        fake_self,
        step=0,
        max_steps=1,
        step_info=None,
        on_step_start=None,
        on_step_end=None,
    )

    # Should return True because history.is_done() is True
    assert result is True

    # Judge must NOT have been called because use_judge is False
    assert calls["judge_called"] is False

    # log_completion should have been awaited
    assert calls["log_completion_called"] is True

    # The async register_done_callback should have been awaited with the history object
    assert calls["register_called_with"] is fake_self.history
