import asyncio
from types import SimpleNamespace
from browser_use.browser.watchdogs import default_action_watchdog
from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog


async def _run_on_send_keys_with_spy(func, fake_self, keys):
    """Helper: patch asyncio.sleep to record delays and run the target function.

    Returns the list of recorded delays (order-preserving).
    """

    recorded = []

    async def spy_sleep(delay):
        # Record the exact numeric value asked for and return immediately
        recorded.append(delay)
        return None

    # Monkeypatch asyncio.sleep for the duration of this call
    original_sleep = asyncio.sleep
    asyncio.sleep = spy_sleep  # type: ignore[assignment]
    try:
        event = SimpleNamespace(keys=keys)
        await func(fake_self, event)
    finally:
        asyncio.sleep = original_sleep
    return recorded


async def _make_minimal_fake():
    """Construct a minimal 'self' surrogate compatible with the on_SendKeysEvent implementation.

    The surrogate provides:
    - browser_session.get_or_create_cdp_session(focus=True) -> cdp_session with cdp_client.send.Input.dispatchKeyEvent
    - _dispatch_key_event async stub (records calls, no sleep)
    - _get_char_modifiers_and_vk(char) and _get_key_code_for_char(base_key)
    - logger.info no-op
    """

    calls = []

    class DummyInput:
        def __init__(self, calls_list):
            self._calls = calls_list

        async def dispatchKeyEvent(self, params=None, session_id=None):
            # record params to allow later inspection if needed
            self._calls.append((params, session_id))
            return {}

    class FakeCDPClient:
        def __init__(self, calls_list):
            # Make send.Input.dispatchKeyEvent available
            self.send = SimpleNamespace(Input=DummyInput(calls_list))

    fake_cdp_session = SimpleNamespace(cdp_client=FakeCDPClient(calls), session_id="fake-session")

    class FakeBrowserSession:
        async def get_or_create_cdp_session(self, focus=True):
            return fake_cdp_session

    class FakeSelf:
        def __init__(self):
            self.browser_session = FakeBrowserSession()
            self.logger = SimpleNamespace(info=lambda *a, **k: None)
            self._dispatched = []

        async def _dispatch_key_event(self, cdp_session, event_type, key, modifiers=None):
            # record minimal info but do not sleep
            self._dispatched.append((event_type, key, modifiers))

        def _get_char_modifiers_and_vk(self, char):
            # Return (modifiers, vk_code, base_key)
            return 0, 0, char

        def _get_key_code_for_char(self, base_key):
            # Return a deterministic code string
            return f'Key{str(base_key).upper()}'

    return FakeSelf()


async def test_probe_001():
    """Probe: ensure only exact 'enter' triggers the post-send Enter sleep (0.1).

    Uses DefaultActionWatchdog.on_SendKeysEvent function object bound to a minimal fake 'self' surrogate so we exercise the real target code path without starting real browser sessions or incurring delays. The test fails if substring matches like 'center' trigger the extra 0.1 sleep.
    """

    # Obtain the target function object (unbound function) from the declared public entrypoint
    target_func = DefaultActionWatchdog.on_SendKeysEvent

    fake = await _make_minimal_fake()

    # Case A: input that should NOT be treated as Enter despite containing 'enter'
    delays_center = await _run_on_send_keys_with_spy(target_func, fake, "center")

    # For a text input like 'center', the implementation should iterate per-character and only use 0.018 sleeps
    # and MUST NOT perform the Enter-specific 0.1 post-send sleep. Assert that 0.1 is not present.
    assert 0.1 not in delays_center, (
        "Invariant violated: substring 'enter' inside 'center' triggered the Enter sleep (0.1)."
    )

    # Also verify we saw per-character sleeps equal to the number of characters in the input
    char_sleep_count_center = sum(1 for d in delays_center if abs(d - 0.018) < 1e-9)
    assert char_sleep_count_center == len("center"), (
        f"Expected {len('center')} per-character sleeps for 'center', got {char_sleep_count_center}: {delays_center}"
    )

    # Case B: input that should be treated as Enter exactly
    # Recreate fake to avoid any residual state differences
    fake2 = await _make_minimal_fake()
    delays_enter = await _run_on_send_keys_with_spy(target_func, fake2, "enter")

    # For 'enter' the normalized key becomes the special 'Enter' and the implementation SHOULD perform the final 0.1 sleep
    assert any(abs(d - 0.1) < 1e-9 for d in delays_enter), (
        "Invariant violated: exact 'enter' did NOT trigger the Enter sleep (0.1)."
    )

    # And verify per-character sleeps are not present for 'enter' (since it is treated as a special key, not text)
    char_sleep_count_enter = sum(1 for d in delays_enter if abs(d - 0.018) < 1e-9)
    assert char_sleep_count_enter == 0, (
        f"Expected 0 per-character sleeps for special key 'enter', got {char_sleep_count_enter}: {delays_enter}"
    )
