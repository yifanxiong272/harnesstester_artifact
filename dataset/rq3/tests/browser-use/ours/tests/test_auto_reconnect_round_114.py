import asyncio
import time
import pytest

import browser_use.browser.session as session_mod

class _FakeLock:
    async def __aenter__(self):
        return None
    async def __aexit__(self, exc_type, exc, tb):
        return False

class _FakeEvent:
    def __init__(self):
        self.cleared = 0
        self.set_count = 0
    def clear(self):
        self.cleared += 1
    def set(self):
        self.set_count += 1

class _FakeEventBus:
    def __init__(self):
        self.events = []
    def dispatch(self, ev):
        self.events.append(ev)

class _FakeLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.errors = []
    def warning(self, msg):
        self.warnings.append(msg)
    def info(self, msg):
        self.infos.append(msg)
    def error(self, msg):
        self.errors.append(msg)

# Minimal stand-ins for the event classes used by _auto_reconnect
class FakeReconnectingEvent:
    def __init__(self, cdp_url, attempt, max_attempts):
        self.cdp_url = cdp_url
        self.attempt = attempt
        self.max_attempts = max_attempts
class FakeReconnectedEvent:
    def __init__(self, cdp_url, attempt, downtime_seconds):
        self.cdp_url = cdp_url
        self.attempt = attempt
        self.downtime_seconds = downtime_seconds
class FakeErrorEvent:
    def __init__(self, error_type, message, details):
        self.error_type = error_type
        self.message = message
        self.details = details

@pytest.mark.asyncio
async def test_auto_reconnect_early_return_round_114(monkeypatch):
    """If _reconnecting is already True the method should return immediately and not dispatch events."""
    fake = type('F', (), {})()
    fake._reconnect_lock = _FakeLock()
    fake._reconnecting = True
    fake._reconnect_event = _FakeEvent()
    fake.event_bus = _FakeEventBus()
    fake.logger = _FakeLogger()
    fake.cdp_url = 'wss://example'

    # Patch event classes so any accidental instantiation would be visible
    monkeypatch.setattr(session_mod, 'BrowserReconnectingEvent', FakeReconnectingEvent)
    monkeypatch.setattr(session_mod, 'BrowserReconnectedEvent', FakeReconnectedEvent)
    monkeypatch.setattr(session_mod, 'BrowserErrorEvent', FakeErrorEvent)

    # Call the bound function with our fake self
    coro = session_mod.BrowserSession._auto_reconnect(fake, max_attempts=3)
    # Awaiting should return quickly and not raise
    await coro

    # No events should have been dispatched and the reconnect_event should be untouched
    assert fake.event_bus.events == []
    assert fake._reconnect_event.set_count == 0
    # The flag should remain True because we returned early (other caller owns it)
    assert fake._reconnecting is True

@pytest.mark.asyncio
async def test_auto_reconnect_success_first_attempt_round_114(monkeypatch):
    """When reconnect succeeds on first attempt, two events (reconnecting + reconnected) are dispatched and _reconnecting is reset."""
    fake = type('F', (), {})()
    fake._reconnect_lock = _FakeLock()
    fake._reconnecting = False
    fake._reconnect_event = _FakeEvent()
    fake.event_bus = _FakeEventBus()
    fake.logger = _FakeLogger()
    fake.cdp_url = 'wss://ok'

    # Provide a reconnect coroutine that completes successfully
    async def _reconnect_ok():
        # simulate a small side-effect
        fake._connected = True
        return None
    fake.reconnect = _reconnect_ok

    # Ensure time is deterministic
    monkeypatch.setattr(time, 'time', lambda: 100.0)

    # Patch asyncio.wait_for to simply await the provided coroutine (deterministic)
    async def _wait_for(coro, timeout):
        return await coro
    monkeypatch.setattr(asyncio, 'wait_for', _wait_for)

    # Patch asyncio.sleep to a no-op and record calls
    sleep_calls = []
    async def _sleep(n):
        sleep_calls.append(n)
        return None
    monkeypatch.setattr(asyncio, 'sleep', _sleep)

    # Patch event classes
    monkeypatch.setattr(session_mod, 'BrowserReconnectingEvent', FakeReconnectingEvent)
    monkeypatch.setattr(session_mod, 'BrowserReconnectedEvent', FakeReconnectedEvent)
    monkeypatch.setattr(session_mod, 'BrowserErrorEvent', FakeErrorEvent)

    await session_mod.BrowserSession._auto_reconnect(fake, max_attempts=3)

    # Two events should be dispatched in order
    assert len(fake.event_bus.events) == 2
    assert isinstance(fake.event_bus.events[0], FakeReconnectingEvent)
    assert fake.event_bus.events[0].attempt == 1
    assert isinstance(fake.event_bus.events[1], FakeReconnectedEvent)
    assert fake.event_bus.events[1].attempt == 1

    # reconnect_event.clear should have been called once and set once in finalizer
    assert fake._reconnect_event.cleared == 1
    assert fake._reconnect_event.set_count == 1

    # _reconnecting must be reset to False after completion
    assert fake._reconnecting is False

    # No sleeps should have been performed because success happened on first attempt
    assert sleep_calls == []

@pytest.mark.asyncio
async def test_auto_reconnect_all_attempts_fail_round_114(monkeypatch):
    """When reconnect raises each attempt, sleep is called between attempts and a BrowserErrorEvent is dispatched after exhaustion."""
    fake = type('F', (), {})()
    fake._reconnect_lock = _FakeLock()
    fake._reconnecting = False
    fake._reconnect_event = _FakeEvent()
    fake.event_bus = _FakeEventBus()
    fake.logger = _FakeLogger()
    fake.cdp_url = 'wss://bad'

    async def _reconnect_fail():
        raise RuntimeError('boom')
    fake.reconnect = _reconnect_fail

    # Deterministic time
    monkeypatch.setattr(time, 'time', lambda: 100.0)

    # Ensure wait_for simply runs coroutine (so our reconnect raises reliably)
    async def _wait_for(coro, timeout):
        return await coro
    monkeypatch.setattr(asyncio, 'wait_for', _wait_for)

    # Capture sleeps performed and make them no-ops
    sleep_calls = []
    async def _sleep(n):
        sleep_calls.append(n)
        return None
    monkeypatch.setattr(asyncio, 'sleep', _sleep)

    # Patch event classes
    monkeypatch.setattr(session_mod, 'BrowserReconnectingEvent', FakeReconnectingEvent)
    monkeypatch.setattr(session_mod, 'BrowserReconnectedEvent', FakeReconnectedEvent)
    monkeypatch.setattr(session_mod, 'BrowserErrorEvent', FakeErrorEvent)

    # Use 2 attempts to exercise the branch where delay is selected for attempt 1 and no sleep after final attempt
    await session_mod.BrowserSession._auto_reconnect(fake, max_attempts=2)

    # Two reconnecting events (one per attempt) and one error event should be dispatched
    assert len(fake.event_bus.events) == 3
    assert isinstance(fake.event_bus.events[0], FakeReconnectingEvent)
    assert isinstance(fake.event_bus.events[1], FakeReconnectingEvent)
    assert isinstance(fake.event_bus.events[2], FakeErrorEvent)
    assert fake.event_bus.events[0].attempt == 1
    assert fake.event_bus.events[1].attempt == 2

    # Sleep should have been called exactly once with the first delay (1.0)
    assert sleep_calls == [1.0]

    # Logger should have recorded warnings for failed attempts and an error for exhaustion
    assert any('Reconnection attempt' in w for w in fake.logger.warnings)
    assert any('All 2 reconnection attempts failed' in e for e in fake.logger.errors)

    # Finalizer should reset flags
    assert fake._reconnect_event.set_count == 1
    assert fake._reconnect_event.cleared == 1
    assert fake._reconnecting is False
