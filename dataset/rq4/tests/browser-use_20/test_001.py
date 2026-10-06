import asyncio
import types

from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog

class _SimpleEvent:
    def __init__(self, keys):
        self.keys = keys

class _Logger:
    def info(self, *args, **kwargs):
        # no-op logger for the watchdog
        return None

def test_probe_001_literal_plus_emits_char_event():
    """When SendKeysEvent.keys is '+', a CDP 'char' event with text '+' must be dispatched.

    This test binds the unbound method DefaultActionWatchdog.on_SendKeysEvent to a
    minimal fake `self` and invokes it. The cdp client dispatchKeyEvent is a
    deterministic async recorder so the test can assert whether a 'char' event
    with text '+' was emitted.
    """

    recorded_params = []

    # Construct fake nested objects: cdp_client.send.Input.dispatchKeyEvent
    class _InputSend:
        def __init__(self, recorder):
            self._recorder = recorder

        async def dispatchKeyEvent(self, params=None, session_id=None, **kwargs):
            # record a shallow copy of params for inspection
            self._recorder.append(dict(params) if params is not None else {})

    class _Send:
        def __init__(self, recorder):
            self.Input = _InputSend(recorder)

    class _CdpClient:
        def __init__(self, recorder):
            self.send = _Send(recorder)

    class _CdpSession:
        def __init__(self, recorder):
            self.cdp_client = _CdpClient(recorder)
            self.session_id = "session-1"

    # browser_session.get_or_create_cdp_session should be async and return the cdp session
    class _BrowserSession:
        def __init__(self, cdp_session):
            self._cdp_session = cdp_session

        async def get_or_create_cdp_session(self, focus=False):
            return self._cdp_session

    # Minimal async _dispatch_key_event used by the combo branch; record its calls too
    dispatch_key_calls = []

    async def _fake_dispatch_key_event(cdp_session, event_type, key, modifiers=0):
        dispatch_key_calls.append((event_type, key, modifiers))
        # do not call real cdp client here - keep deterministic
        return None

    # Build fake self with the required attributes used by the method
    cdp_session = _CdpSession(recorded_params)
    browser_session = _BrowserSession(cdp_session)

    fake_self = types.SimpleNamespace(
        browser_session=browser_session,
        logger=_Logger(),
        _dispatch_key_event=_fake_dispatch_key_event,
    )

    # Construct the event with a single plus character
    event = _SimpleEvent(keys='+')

    # Bind the unbound coroutine function to our fake self
    bound_coro = DefaultActionWatchdog.on_SendKeysEvent.__get__(fake_self, DefaultActionWatchdog)

    # Run the coroutine synchronously for the test
    asyncio.run(bound_coro(event))

    # Primary observable: recorded_params should include a 'char' event with text '+'
    found_char_plus = any(
        (call.get('type') == 'char' and call.get('text') == '+')
        for call in recorded_params
    )

    assert found_char_plus, (
        "Expected a CDP 'char' dispatch with text '+', but none was recorded. "
        f"Recorded params: {recorded_params}, _dispatch_key_event calls: {dispatch_key_calls}"
    )
