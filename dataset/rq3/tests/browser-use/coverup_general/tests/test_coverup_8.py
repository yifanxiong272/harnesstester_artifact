# file: browser_use/browser/watchdogs/default_action_watchdog.py:2446-2649
# asked: {"lines": [2448, 2449, 2451, 2452, 2453, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2474, 2475, 2479, 2480, 2482, 2483, 2484, 2485, 2486, 2487, 2488, 2491, 2492, 2495, 2496, 2497, 2498, 2501, 2502, 2503, 2504, 2507, 2508, 2511, 2513, 2516, 2517, 2520, 2553, 2554, 2556, 2557, 2558, 2559, 2560, 2561, 2563, 2565, 2569, 2571, 2572, 2573, 2574, 2575, 2576, 2577, 2579, 2581, 2582, 2583, 2584, 2585, 2586, 2588, 2590, 2591, 2592, 2593, 2594, 2595, 2597, 2599, 2602, 2603, 2606, 2607, 2608, 2609, 2610, 2611, 2612, 2614, 2618, 2619, 2620, 2621, 2622, 2624, 2628, 2629, 2630, 2631, 2632, 2633, 2634, 2636, 2640, 2642, 2646, 2647, 2648, 2649], "branches": [[2480, 2482], [2480, 2491], [2484, 2485], [2484, 2488], [2495, 2496], [2495, 2520], [2503, 2504], [2503, 2507], [2507, 2508], [2507, 2511], [2516, 2517], [2516, 2642], [2553, 2554], [2553, 2569], [2556, 2557], [2556, 2565], [2569, 2571], [2569, 2642], [2571, 2572], [2571, 2602], [2646, 0], [2646, 2647]]}
# gained: {"lines": [2448, 2449, 2451, 2452, 2453, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2474, 2475, 2479, 2480, 2482, 2483, 2484, 2485, 2486, 2487, 2488, 2491, 2492, 2495, 2496, 2497, 2498, 2501, 2502, 2503, 2504, 2507, 2508, 2511, 2513, 2516, 2517, 2520, 2553, 2554, 2556, 2557, 2558, 2559, 2560, 2561, 2563, 2565, 2569, 2571, 2572, 2573, 2574, 2575, 2576, 2577, 2579, 2581, 2582, 2583, 2584, 2585, 2586, 2588, 2590, 2591, 2592, 2593, 2594, 2595, 2597, 2599, 2602, 2603, 2606, 2607, 2608, 2609, 2610, 2611, 2612, 2614, 2618, 2619, 2620, 2621, 2622, 2624, 2628, 2629, 2630, 2631, 2632, 2633, 2634, 2636, 2640, 2642, 2646, 2647, 2648, 2649], "branches": [[2480, 2482], [2480, 2491], [2484, 2485], [2484, 2488], [2495, 2496], [2495, 2520], [2503, 2504], [2503, 2507], [2507, 2508], [2507, 2511], [2516, 2517], [2516, 2642], [2553, 2554], [2553, 2569], [2556, 2557], [2569, 2571], [2569, 2642], [2571, 2572], [2571, 2602], [2646, 0], [2646, 2647]]}

import asyncio
import pytest
from types import SimpleNamespace

from browser_use.browser.watchdogs.default_action_watchdog import DefaultActionWatchdog


@pytest.mark.asyncio
async def test_sendkeys_combo_modifiers(monkeypatch):
    # Create instance without running Pydantic __init__
    wd = object.__new__(DefaultActionWatchdog)
    # Provide pydantic internals to allow attribute setting
    object.__setattr__(wd, "__pydantic_fields_set__", set())

    # Prepare browser_session with logger and get_or_create_cdp_session
    fake_cdp_session = SimpleNamespace(
        session_id="sid",
        cdp_client=SimpleNamespace(send=SimpleNamespace(Input=SimpleNamespace(dispatchKeyEvent=lambda *a, **k: None))),
    )

    async def fake_get_or_create_cdp_session(focus=True):
        return fake_cdp_session

    wd.browser_session = SimpleNamespace(
        get_or_create_cdp_session=fake_get_or_create_cdp_session,
        logger=SimpleNamespace(info=lambda *a, **k: None),
    )

    # Record dispatched key events (from _dispatch_key_event)
    dispatch_calls = []

    async def fake_dispatch_key_event(cdp_session, event_type, key, modifiers=0):
        dispatch_calls.append((event_type, key, modifiers))

    wd._dispatch_key_event = fake_dispatch_key_event

    # Replace asyncio.sleep with async no-op to avoid delays
    async def _nosleep(_=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # Event with modifiers
    event = SimpleNamespace(keys="ctrl+Alt+a")

    # Call the method
    await wd.on_SendKeysEvent(event)

    # Expected sequence:
    # keyDown Control
    # keyDown Alt
    # keyDown main_key 'a' with modifiers bitmask (Control=2,Alt=1 => 3)
    # keyUp main_key 'a' with modifier 3
    # keyUp Alt
    # keyUp Control
    assert dispatch_calls[0] == ("keyDown", "Control", 0)
    assert dispatch_calls[1] == ("keyDown", "Alt", 0)
    assert dispatch_calls[2] == ("keyDown", "a", 3)
    assert dispatch_calls[3] == ("keyUp", "a", 3)
    assert dispatch_calls[4] == ("keyUp", "Alt", 0)
    assert dispatch_calls[5] == ("keyUp", "Control", 0)
    assert len(dispatch_calls) == 6


@pytest.mark.asyncio
async def test_sendkeys_enter_special_key_dispatch_char(monkeypatch):
    wd = object.__new__(DefaultActionWatchdog)
    object.__setattr__(wd, "__pydantic_fields_set__", set())

    # Prepare fake input dispatch recorder
    cdp_input_calls = []

    async def fake_dispatchKeyEvent(params=None, session_id=None):
        cdp_input_calls.append({"params": params, "session_id": session_id})

    fake_input = SimpleNamespace(dispatchKeyEvent=fake_dispatchKeyEvent)
    fake_cdp_session = SimpleNamespace(
        session_id="session-123",
        cdp_client=SimpleNamespace(send=SimpleNamespace(Input=fake_input)),
    )

    async def fake_get_or_create_cdp_session(focus=True):
        return fake_cdp_session

    wd.browser_session = SimpleNamespace(
        get_or_create_cdp_session=fake_get_or_create_cdp_session,
        logger=SimpleNamespace(info=lambda *a, **k: None),
    )

    # Record calls to _dispatch_key_event
    dispatch_calls = []

    async def fake_dispatch_key_event(cdp_session, event_type, key, modifiers=0):
        dispatch_calls.append((event_type, key, modifiers))

    wd._dispatch_key_event = fake_dispatch_key_event

    # Avoid sleeps
    async def _nosleep(_=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    event = SimpleNamespace(keys="Enter")

    await wd.on_SendKeysEvent(event)

    # Expect a keyDown and keyUp for Enter via _dispatch_key_event
    assert ("keyDown", "Enter", 0) in dispatch_calls
    assert ("keyUp", "Enter", 0) in dispatch_calls

    # Expect the cdp Input.dispatchKeyEvent to have been called once with type 'char' and text '\r'
    found = False
    for call in cdp_input_calls:
        params = call["params"] or {}
        if params.get("type") == "char" and params.get("text") == "\r" and params.get("key") == "Enter":
            found = True
            assert call["session_id"] == "session-123"
    assert found, f"Expected char dispatch for Enter not found in {cdp_input_calls}"


@pytest.mark.asyncio
async def test_sendkeys_text_with_newline_and_chars(monkeypatch):
    wd = object.__new__(DefaultActionWatchdog)
    object.__setattr__(wd, "__pydantic_fields_set__", set())

    # Prepare fake input dispatch recorder
    cdp_input_calls = []

    async def fake_dispatchKeyEvent(params=None, session_id=None):
        cdp_input_calls.append({"params": params, "session_id": session_id})

    fake_input = SimpleNamespace(dispatchKeyEvent=fake_dispatchKeyEvent)
    fake_cdp_session = SimpleNamespace(
        session_id="sess-x",
        cdp_client=SimpleNamespace(send=SimpleNamespace(Input=fake_input)),
    )

    async def fake_get_or_create_cdp_session(focus=True):
        return fake_cdp_session

    wd.browser_session = SimpleNamespace(
        get_or_create_cdp_session=fake_get_or_create_cdp_session,
        logger=SimpleNamespace(info=lambda *a, **k: None),
    )

    # Provide implementations for char helpers
    async def _dummy_dispatch(*args, **kwargs):
        # Not used in this text path
        raise AssertionError("Should not be called in this test")

    wd._dispatch_key_event = _dummy_dispatch

    # _get_char_modifiers_and_vk returns (modifiers, vk_code, base_key)
    def fake_get_char_modifiers_and_vk(ch):
        # Return deterministic values
        if ch == "\n" or ch == "\r":
            return (0, 13, "Enter")
        return (0, ord(ch.upper()), ch)

    def fake_get_key_code_for_char(ch):
        # Return a code string
        return f"Key{ch.upper()}"

    wd._get_char_modifiers_and_vk = fake_get_char_modifiers_and_vk
    wd._get_key_code_for_char = fake_get_key_code_for_char

    # Replace asyncio.sleep with no-op to avoid delays
    async def _nosleep(_=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # Provide event containing 'a', newline, 'b'
    event = SimpleNamespace(keys="a\nb")

    await wd.on_SendKeysEvent(event)

    # We expect sequence:
    # For 'a': keyDown (type 'keyDown'), char (type 'char'), keyUp (type 'keyUp')
    # For '\n': rawKeyDown, char, keyUp with windowsVirtualKeyCode 13 and text '\r'
    # For 'b': keyDown, char, keyUp
    types_sequence = [call["params"]["type"] for call in cdp_input_calls]
    # Flatten expected types
    expected_sequence = [
        "keyDown", "char", "keyUp",
        "rawKeyDown", "char", "keyUp",
        "keyDown", "char", "keyUp",
    ]
    assert types_sequence == expected_sequence, f"Unexpected types: {types_sequence}"

    # Check the newline block parameters (positions 3,4,5)
    nl_raw = cdp_input_calls[3]["params"]
    assert nl_raw["type"] == "rawKeyDown" and nl_raw["windowsVirtualKeyCode"] == 13
    nl_char = cdp_input_calls[4]["params"]
    assert nl_char["type"] == "char" and nl_char["text"] == "\r"
    nl_keyup = cdp_input_calls[5]["params"]
    assert nl_keyup["type"] == "keyUp" and nl_keyup["windowsVirtualKeyCode"] == 13

    # Verify session_id used consistently
    for call in cdp_input_calls:
        assert call["session_id"] == "sess-x"


@pytest.mark.asyncio
async def test_sendkeys_exception_is_reraised(monkeypatch):
    wd = object.__new__(DefaultActionWatchdog)
    object.__setattr__(wd, "__pydantic_fields_set__", set())

    # Fake cdp_session
    fake_cdp_session = SimpleNamespace(
        session_id="sid-ex",
        cdp_client=SimpleNamespace(send=SimpleNamespace(Input=SimpleNamespace(dispatchKeyEvent=lambda *a, **k: None))),
    )

    async def fake_get_or_create_cdp_session(focus=True):
        return fake_cdp_session

    wd.browser_session = SimpleNamespace(
        get_or_create_cdp_session=fake_get_or_create_cdp_session,
        logger=SimpleNamespace(info=lambda *a, **k: None),
    )

    # Make _dispatch_key_event raise to trigger except/re-raise
    async def raising_dispatch(cdp_session, event_type, key, modifiers=0):
        raise RuntimeError("boom")

    wd._dispatch_key_event = raising_dispatch

    # Avoid sleeps
    async def _nosleep(_=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    event = SimpleNamespace(keys="Enter")

    with pytest.raises(RuntimeError):
        await wd.on_SendKeysEvent(event)
