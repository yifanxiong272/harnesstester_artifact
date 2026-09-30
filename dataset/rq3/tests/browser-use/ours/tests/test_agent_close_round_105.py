import asyncio
import gc
import pytest

from browser_use.agent.service import Agent
from browser_use.browser.events import _get_timeout


class DummyLogger:
    def __init__(self):
        self.debug_messages = []
        self.error_messages = []

    def debug(self, msg):
        # store as string for deterministic assertions
        self.debug_messages.append(str(msg))

    def error(self, msg):
        self.error_messages.append(str(msg))


class DummyBrowserProfile:
    def __init__(self, keep_alive: bool):
        self.keep_alive = keep_alive


class DummyEventBusBadSetter:
    def __init__(self):
        self.stop_called_args = None

    async def stop(self, clear, timeout):
        # emulate asynchronous stop call
        self.stop_called_args = (clear, timeout)

    def __setattr__(self, name, value):
        # raise when tests attempt to set event_queue or _on_idle to trigger the except branch
        if name in ("event_queue", "_on_idle"):
            raise Exception("cannot set")
        object.__setattr__(self, name, value)


class DummyEventBusOk:
    def __init__(self):
        self.stop_called_args = None
        self.event_queue = "initial"
        self._on_idle = "initial"

    async def stop(self, clear, timeout):
        self.stop_called_args = (clear, timeout)


class DummyBrowserSession:
    def __init__(self, keep_alive: bool, use_bad_event_bus: bool = False):
        self.browser_profile = DummyBrowserProfile(keep_alive)
        self.kill_called = False
        self.event_bus = DummyEventBusBadSetter() if use_bad_event_bus else DummyEventBusOk()

    async def kill(self):
        self.kill_called = True


class DummySkillService:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


# Patch Agent.logger property for the duration of this test module so we can inject DummyLogger instances.
_original_logger_prop = getattr(Agent, "logger", None)

def _make_test_logger_property():
    def fget(self):
        # tests will set instance._test_logger when they need to observe logs
        return self.__dict__.get("_test_logger", DummyLogger())

    return property(fget)

Agent.logger = _make_test_logger_property()


@pytest.fixture(scope="module", autouse=True)
def _restore_agent_logger_prop():
    # After all tests in this module, restore original Agent.logger
    try:
        yield
    finally:
        if _original_logger_prop is not None:
            Agent.logger = _original_logger_prop


@pytest.mark.asyncio
async def test_close_no_browser_no_skill_no_tasks_round_105():
    """No browser_session and no skill_service: should still run GC and log threads; no asyncio-tasks log."""
    agent = Agent.__new__(Agent)
    agent.browser_session = None
    agent.skill_service = None
    agent._test_logger = DummyLogger()

    # patch gc.collect temporarily
    orig_gc_collect = gc.collect
    called = {"gc": False}

    def fake_collect():
        called["gc"] = True

    gc.collect = fake_collect
    try:
        await agent.close()
    finally:
        gc.collect = orig_gc_collect

    assert called["gc"] is True
    # logger.debug should contain a message about remaining threads
    debug_msgs = agent._test_logger.debug_messages
    assert any("Remaining threads" in m for m in debug_msgs)
    # should NOT log remaining asyncio tasks in this scenario
    assert not any("Remaining asyncio tasks" in m for m in debug_msgs)
    # no errors should be logged
    assert agent._test_logger.error_messages == []


@pytest.mark.asyncio
async def test_close_browser_kill_round_105():
    """When browser_profile.keep_alive is False, kill() is awaited on browser_session."""
    agent = Agent.__new__(Agent)
    agent.browser_session = DummyBrowserSession(keep_alive=False)
    agent.skill_service = None
    agent._test_logger = DummyLogger()

    # ensure gc.collect is no-op for determinism
    orig_gc_collect = gc.collect
    gc.collect = lambda: None
    try:
        await agent.close()
    finally:
        gc.collect = orig_gc_collect

    assert agent.browser_session.kill_called is True
    # should not attempt to call event_bus.stop in this branch
    # event_bus for this session is the ok variant; stop_called_args remains None
    assert getattr(agent.browser_session.event_bus, "stop_called_args", None) is None


@pytest.mark.asyncio
async def test_close_browser_keep_alive_and_event_bus_exception_round_105():
    """When keep_alive is True and event_bus attribute setting raises, ensure stop() awaited and exception swallowed."""
    agent = Agent.__new__(Agent)
    # event bus whose attribute setting raises to hit the inner except branch
    agent.browser_session = DummyBrowserSession(keep_alive=True, use_bad_event_bus=True)
    agent.skill_service = None
    agent._test_logger = DummyLogger()

    # patch gc.collect as noop
    orig_gc_collect = gc.collect
    gc.collect = lambda: None
    try:
        await agent.close()
    finally:
        gc.collect = orig_gc_collect

    # stop should have been called with clear=False and the module timeout lookup
    stop_args = agent.browser_session.event_bus.stop_called_args
    assert stop_args is not None
    clear_arg, timeout_arg = stop_args
    assert clear_arg is False
    # validate timeout comes from _get_timeout contract (numeric)
    expected_timeout = _get_timeout('TIMEOUT_BrowserSessionEventBusStopOnAgentClose', 1.0)
    assert timeout_arg == expected_timeout
    # because the event_bus setter raises, no attributes should have been set - but code swallows the exception
    # confirm no error logged at outer level
    assert agent._test_logger.error_messages == []


@pytest.mark.asyncio
async def test_close_skill_service_and_other_tasks_logging_round_105():
    """When skill_service is present it should be closed; when other asyncio tasks exist they are logged."""
    agent = Agent.__new__(Agent)
    agent.browser_session = None
    agent.skill_service = DummySkillService()
    agent._test_logger = DummyLogger()

    # Create a background task that will remain pending during close to ensure other_tasks non-empty
    pending_event = asyncio.Event()

    async def wait_forever(ev: asyncio.Event):
        await ev.wait()

    bg_task = asyncio.create_task(wait_forever(pending_event))
    # give a deterministic name if supported
    try:
        try:
            bg_task.set_name("bg_task")
        except Exception:
            # older python versions may not support set_name on Task
            pass

        # patch gc.collect as noop
        orig_gc_collect = gc.collect
        gc.collect = lambda: None
        try:
            await agent.close()
        finally:
            gc.collect = orig_gc_collect

        # skill service should be closed
        assert agent.skill_service.closed is True

        # logger.debug should have recorded remaining asyncio tasks
        assert any("Remaining asyncio tasks" in m for m in agent._test_logger.debug_messages)
        # one of the debug messages should reference the bg_task name we set
        assert any("bg_task" in m or "wait_forever" in m for m in agent._test_logger.debug_messages)

    finally:
        # clean up the background task
        pending_event.set()
        await asyncio.sleep(0)  # allow task to wake and finish
        if not bg_task.done():
            bg_task.cancel()
            try:
                await bg_task
            except Exception:
                pass


@pytest.mark.asyncio
async def test_close_outer_exception_logs_error_round_105():
    """If an unexpected exception occurs during cleanup, it should be caught and logged via logger.error."""
    agent = Agent.__new__(Agent)
    agent.browser_session = None
    agent.skill_service = None
    agent._test_logger = DummyLogger()

    # Make gc.collect raise to trigger outer except
    orig_gc_collect = gc.collect

    def raising_collect():
        raise RuntimeError("boom")

    gc.collect = raising_collect
    try:
        await agent.close()
    finally:
        gc.collect = orig_gc_collect

    # ensure error was logged and contains our message
    assert any("Error during cleanup" in m for m in agent._test_logger.error_messages)
    assert any("boom" in m for m in agent._test_logger.error_messages)
