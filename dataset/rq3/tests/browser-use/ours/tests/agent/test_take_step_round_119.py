import inspect
import pytest
from types import SimpleNamespace
from browser_use.agent.service import Agent

# Helper to call the unbound async method Agent.take_step with a fake self
async def _call_take_step_with_self(fake_self, step_info):
    # Agent.take_step is an async function defined on the class; call it with the fake_self
    return await Agent.take_step(fake_self, step_info)

@pytest.mark.asyncio
async def test_take_step_initial_interrupted_async_callback_round_119():
    called = {
        "first_start": False,
        "initial_actions": False,
        "step": False,
        "log_completion": False,
        "judge": False,
        "done_cb_received_history": None,
    }

    async def _execute_initial_actions():
        called["initial_actions"] = True
        # Simulate an InterruptedError that should be caught and ignored
        raise InterruptedError("interrupted")

    async def step(step_info):
        called["step"] = True

    async def log_completion():
        called["log_completion"] = True

    async def _judge_and_log():
        called["judge"] = True

    async def register_done_callback(history):
        # store the passed history object to verify it was forwarded
        called["done_cb_received_history"] = history

    def _log_first_step_startup():
        called["first_start"] = True

    # history object that reports done
    history = SimpleNamespace(is_done=lambda: True)

    fake_self = SimpleNamespace()
    fake_self._log_first_step_startup = _log_first_step_startup
    fake_self._execute_initial_actions = _execute_initial_actions
    fake_self.step = step
    fake_self.history = history
    fake_self.log_completion = log_completion
    fake_self.settings = SimpleNamespace(use_judge=True)
    fake_self._judge_and_log = _judge_and_log
    fake_self.register_done_callback = register_done_callback

    # step_info with step_number == 0 to hit the initial-actions branch
    step_info = SimpleNamespace(step_number=0)

    result = await _call_take_step_with_self(fake_self, step_info)

    assert result == (True, True)
    # Ensure the startup hook ran
    assert called["first_start"] is True
    # initial actions were attempted (raised InterruptedError but should be caught)
    assert called["initial_actions"] is True
    # step was executed
    assert called["step"] is True
    # completion & judge ran
    assert called["log_completion"] is True
    assert called["judge"] is True
    # the async done callback was awaited and received the same history object
    assert called["done_cb_received_history"] is history


@pytest.mark.asyncio
async def test_take_step_initial_raises_non_interrupted_round_119():
    # If _execute_initial_actions raises a non-InterruptedError, take_step should propagate it
    called = {"step": False}

    async def _execute_initial_actions():
        raise ValueError("fatal")

    async def step(step_info):
        called["step"] = True

    def _log_first_step_startup():
        pass

    fake_self = SimpleNamespace()
    fake_self._log_first_step_startup = _log_first_step_startup
    fake_self._execute_initial_actions = _execute_initial_actions
    fake_self.step = step
    fake_self.history = SimpleNamespace(is_done=lambda: False)
    # use_judge and others irrelevant here
    fake_self.settings = SimpleNamespace(use_judge=False)

    step_info = SimpleNamespace(step_number=0)

    with pytest.raises(ValueError):
        await _call_take_step_with_self(fake_self, step_info)

    # ensure step was NOT executed because the exception should have been re-raised
    assert called["step"] is False


@pytest.mark.asyncio
async def test_take_step_no_initial_history_not_done_round_119():
    # When no initial actions branch (step_info None), and history.is_done() is False,
    # take_step should call step and return (False, False)
    called = {"step_called_with": None}

    async def step(step_info):
        called["step_called_with"] = step_info

    fake_self = SimpleNamespace()
    fake_self._log_first_step_startup = lambda: (_ for _ in ()).throw(AssertionError("should not be called"))
    # _execute_initial_actions should not be referenced
    fake_self._execute_initial_actions = lambda: (_ for _ in ()).throw(AssertionError("should not be called"))
    fake_self.step = step
    fake_self.history = SimpleNamespace(is_done=lambda: False)
    fake_self.settings = SimpleNamespace(use_judge=True)

    result = await _call_take_step_with_self(fake_self, None)

    assert result == (False, False)
    # step should have been called with the same None step_info
    assert called["step_called_with"] is None


@pytest.mark.asyncio
async def test_take_step_register_done_callback_sync_and_no_judge_round_119():
    # Test branch where history.is_done() True, but settings.use_judge is False, and the
    # register_done_callback is a sync function (not coroutine). The sync callback should be called.
    flags = {"log_completion": False, "done_cb_called": False}

    async def step(step_info):
        # nothing else
        return None

    async def log_completion():
        flags["log_completion"] = True

    def register_done_callback(history):
        # sync callback should be called and receive history
        flags["done_cb_called"] = True
        # verify the history object is the same object on fake_self
        assert history is fake_self.history

    fake_self = SimpleNamespace()
    fake_self._log_first_step_startup = lambda: None
    fake_self._execute_initial_actions = lambda: None
    fake_self.step = step
    fake_self.history = SimpleNamespace(is_done=lambda: True)
    fake_self.log_completion = log_completion
    fake_self.settings = SimpleNamespace(use_judge=False)
    fake_self.register_done_callback = register_done_callback

    result = await _call_take_step_with_self(fake_self, None)

    assert result == (True, True)
    assert flags["log_completion"] is True
    assert flags["done_cb_called"] is True
