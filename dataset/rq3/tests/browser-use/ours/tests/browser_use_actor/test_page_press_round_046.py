import pytest
from types import SimpleNamespace
import inspect

import browser_use.actor.page as page_module
from browser_use.actor.page import Page

# Helper fake Input sender to capture dispatched events
class DummyInput:
    def __init__(self, calls):
        self.calls = calls

    async def dispatchKeyEvent(self, params, session_id=None):
        # copy params to freeze current shape
        self.calls.append((dict(params), session_id))
        return None

@pytest.mark.asyncio
async def test_press_with_modifiers_round_046(monkeypatch):
    # Arrange: capture dispatch calls
    calls = []
    dummy_input = DummyInput(calls)
    fake_send = SimpleNamespace(Input=dummy_input)
    fake_client = SimpleNamespace(send=fake_send)

    # Create Page instance without running its real __init__
    p = Page.__new__(Page)
    # _ensure_session should be an async callable returning a session id
    async def _ensure_session():
        return "session-123"
    p._ensure_session = _ensure_session
    p._client = fake_client

    # Patch get_key_info in the module under test to control vk_code presence
    def fake_get_key_info(key):
        # For modifiers, return a vk_code to hit the branches that add windowsVirtualKeyCode
        if key == "Control":
            return ("ControlCode", 17)
        # For main key A, also return a vk code
        if key == "A":
            return ("KeyA", 65)
        # Fallback
        return (f"Code_{key}", None)

    monkeypatch.setattr(page_module, "get_key_info", fake_get_key_info)

    # Act: press a combination
    await p.press("Control+A")

    # Assert: we expect four dispatchKeyEvent calls in this order:
    # 1) modifier keyDown
    # 2) main keyDown (with modifiers bitmask)
    # 3) main keyUp (with modifiers bitmask)
    # 4) modifier keyUp
    assert len(calls) == 4, f"expected 4 dispatch calls, got {len(calls)}"

    # 1) modifier keyDown
    params_1, sid_1 = calls[0]
    assert sid_1 == "session-123"
    assert params_1["type"] == "keyDown"
    assert params_1["key"] == "Control"
    assert params_1["code"] == "ControlCode"
    # windowsVirtualKeyCode added for modifiers with vk_code
    assert params_1.get("windowsVirtualKeyCode") == 17

    # 2) main keyDown should include modifiers bitmask for Control -> 2
    params_2, sid_2 = calls[1]
    assert sid_2 == "session-123"
    assert params_2["type"] == "keyDown"
    assert params_2["key"] == "A"
    assert params_2["code"] == "KeyA"
    assert params_2["modifiers"] == 2
    assert params_2.get("windowsVirtualKeyCode") == 65

    # 3) main keyUp should mirror modifiers bitmask and include vk code
    params_3, sid_3 = calls[2]
    assert sid_3 == "session-123"
    assert params_3["type"] == "keyUp"
    assert params_3["key"] == "A"
    assert params_3["code"] == "KeyA"
    assert params_3["modifiers"] == 2
    assert params_3.get("windowsVirtualKeyCode") == 65

    # 4) modifier keyUp should be for Control with vk code
    params_4, sid_4 = calls[3]
    assert sid_4 == "session-123"
    assert params_4["type"] == "keyUp"
    assert params_4["key"] == "Control"
    assert params_4["code"] == "ControlCode"
    assert params_4.get("windowsVirtualKeyCode") == 17


@pytest.mark.asyncio
async def test_press_simple_key_no_vk_round_046(monkeypatch):
    # Arrange: capture dispatch calls
    calls = []
    dummy_input = DummyInput(calls)
    fake_send = SimpleNamespace(Input=dummy_input)
    fake_client = SimpleNamespace(send=fake_send)

    p = Page.__new__(Page)
    async def _ensure_session():
        return "sess-xyz"
    p._ensure_session = _ensure_session
    p._client = fake_client

    # Patch get_key_info to return no windowsVirtualKeyCode for simple key
    def fake_get_key_info_no_vk(key):
        return ("KeyZ", None)

    monkeypatch.setattr(page_module, "get_key_info", fake_get_key_info_no_vk)

    # Act: press a simple key without '+' to hit the else branch
    await p.press("z")

    # Assert: two dispatches (keyDown, keyUp) and no windowsVirtualKeyCode present
    assert len(calls) == 2

    params_down, sid_down = calls[0]
    assert sid_down == "sess-xyz"
    assert params_down["type"] == "keyDown"
    assert params_down["key"] == "z"
    assert params_down["code"] == "KeyZ"
    assert "windowsVirtualKeyCode" not in params_down

    params_up, sid_up = calls[1]
    assert sid_up == "sess-xyz"
    assert params_up["type"] == "keyUp"
    assert params_up["key"] == "z"
    assert params_up["code"] == "KeyZ"
    assert "windowsVirtualKeyCode" not in params_up
