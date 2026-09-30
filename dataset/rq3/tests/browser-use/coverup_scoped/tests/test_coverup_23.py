# file: browser_use/actor/page.py:213-277
# asked: {"lines": [215, 218, 219, 220, 221, 224, 225, 226, 227, 230, 231, 232, 233, 234, 235, 238, 239, 240, 241, 242, 243, 245, 246, 247, 249, 250, 251, 252, 253, 255, 256, 257, 260, 261, 262, 263, 264, 265, 268, 269, 270, 271, 272, 274, 275, 276, 277], "branches": [[218, 219], [218, 268], [226, 227], [226, 230], [230, 231], [230, 238], [233, 234], [233, 235], [245, 246], [245, 247], [255, 256], [255, 257], [260, 0], [260, 261], [263, 264], [263, 265], [270, 271], [270, 272], [275, 276], [275, 277]]}
# gained: {"lines": [215, 218, 219, 220, 221, 224, 225, 226, 227, 230, 231, 232, 233, 234, 235, 238, 239, 240, 241, 242, 243, 245, 247, 249, 250, 251, 252, 253, 255, 257, 260, 261, 262, 263, 264, 265, 268, 269, 270, 271, 272, 274, 275, 276, 277], "branches": [[218, 219], [218, 268], [226, 227], [226, 230], [230, 231], [230, 238], [233, 234], [245, 247], [255, 257], [260, 0], [260, 261], [263, 264], [270, 271], [275, 276]]}

import pytest
import types
from types import SimpleNamespace
import asyncio

import browser_use.actor.page as page_module
from browser_use.actor.page import Page

@pytest.mark.asyncio
async def test_press_with_modifier(monkeypatch):
    # Prepare capture list for dispatch calls
    calls = []

    class Input:
        async def dispatchKeyEvent(self, params, session_id=None):
            # simulate async work
            await asyncio.sleep(0)
            calls.append((params, session_id))

    # Create fake cdp_client with send.Input
    fake_client = SimpleNamespace(send=SimpleNamespace(Input=Input()))
    browser_session = SimpleNamespace(cdp_client=fake_client)

    page = Page(browser_session, target_id="target-1")

    # Replace _ensure_session to return a deterministic session id
    async def fake_ensure_session(self):
        return "session-ctrl-x"
    monkeypatch.setattr(page_module.Page, "_ensure_session", fake_ensure_session)

    # Monkeypatch get_key_info in the page module (that's where it's looked up)
    def fake_get_key_info(key):
        mapping = {
            "Control": ("ControlLeft", 17),
            "X": ("KeyX", None),
        }
        return mapping[key]
    monkeypatch.setattr(page_module, "get_key_info", fake_get_key_info)

    # Call the method under test
    await page.press("Control+X")

    # Expect 4 calls: modifier keyDown, main keyDown, main keyUp, modifier keyUp
    assert len(calls) == 4

    # Validate order and content
    first_params, first_session = calls[0]
    assert first_session == "session-ctrl-x"
    assert first_params["type"] == "keyDown"
    assert first_params["key"] == "Control"
    assert first_params["code"] == "ControlLeft"
    assert first_params["windowsVirtualKeyCode"] == 17

    second_params, second_session = calls[1]
    assert second_session == "session-ctrl-x"
    assert second_params["type"] == "keyDown"
    assert second_params["key"] == "X"
    assert second_params["code"] == "KeyX"
    # Modifier bitmask: Control -> 2
    assert second_params["modifiers"] == 2
    assert "windowsVirtualKeyCode" not in second_params  # main vk_code was None

    third_params, third_session = calls[2]
    assert third_session == "session-ctrl-x"
    assert third_params["type"] == "keyUp"
    assert third_params["key"] == "X"
    assert third_params["code"] == "KeyX"
    assert third_params["modifiers"] == 2
    assert "windowsVirtualKeyCode" not in third_params

    fourth_params, fourth_session = calls[3]
    assert fourth_session == "session-ctrl-x"
    assert fourth_params["type"] == "keyUp"
    assert fourth_params["key"] == "Control"
    assert fourth_params["code"] == "ControlLeft"
    assert fourth_params["windowsVirtualKeyCode"] == 17

@pytest.mark.asyncio
async def test_press_simple_key_with_vk(monkeypatch):
    # Prepare capture list for dispatch calls
    calls = []

    class Input:
        async def dispatchKeyEvent(self, params, session_id=None):
            await asyncio.sleep(0)
            calls.append((params, session_id))

    fake_client = SimpleNamespace(send=SimpleNamespace(Input=Input()))
    browser_session = SimpleNamespace(cdp_client=fake_client)
    page = Page(browser_session, target_id="t2")

    # Replace _ensure_session
    async def fake_ensure_session(self):
        return "session-z"
    monkeypatch.setattr(page_module.Page, "_ensure_session", fake_ensure_session)

    # Monkeypatch get_key_info to provide a windowsVirtualKeyCode for 'Z'
    def fake_get_key_info(key):
        mapping = {
            "Z": ("KeyZ", 90),
        }
        return mapping[key]
    monkeypatch.setattr(page_module, "get_key_info", fake_get_key_info)

    await page.press("Z")

    # Expect 2 calls: keyDown and keyUp
    assert len(calls) == 2

    down_params, down_session = calls[0]
    up_params, up_session = calls[1]

    assert down_session == "session-z"
    assert down_params["type"] == "keyDown"
    assert down_params["key"] == "Z"
    assert down_params["code"] == "KeyZ"
    assert down_params["windowsVirtualKeyCode"] == 90

    assert up_session == "session-z"
    assert up_params["type"] == "keyUp"
    assert up_params["key"] == "Z"
    assert up_params["code"] == "KeyZ"
    assert up_params["windowsVirtualKeyCode"] == 90
