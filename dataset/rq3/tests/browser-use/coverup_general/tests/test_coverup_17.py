# file: browser_use/actor/element.py:353-507
# asked: {"lines": [355, 357, 358, 359, 362, 365, 366, 367, 368, 369, 372, 373, 374, 376, 377, 378, 381, 382, 383, 384, 385, 386, 388, 390, 391, 392, 393, 394, 395, 396, 397, 400, 401, 404, 405, 406, 407, 408, 409, 413, 414, 415, 417, 418, 421, 423, 425, 427, 428, 429, 430, 431, 432, 434, 438, 441, 442, 443, 444, 445, 447, 451, 452, 453, 454, 455, 456, 458, 463, 464, 467, 468, 469, 470, 471, 472, 473, 475, 479, 482, 483, 484, 485, 486, 488, 492, 493, 494, 495, 496, 497, 498, 500, 504, 506, 507], "branches": [[376, 377], [376, 378], [390, 391], [390, 400], [400, 401], [400, 404], [413, 414], [413, 421], [417, 418], [417, 421], [423, 0], [423, 425], [425, 427], [425, 463]]}
# gained: {"lines": [355, 357, 358, 359, 362, 365, 366, 367, 368, 369, 372, 373, 374, 376, 377, 378, 381, 382, 383, 384, 385, 386, 388, 390, 391, 392, 393, 394, 395, 400, 401, 404, 405, 406, 407, 408, 409, 413, 414, 415, 417, 421, 423, 425, 427, 428, 429, 430, 431, 432, 434, 438, 441, 442, 443, 444, 445, 447, 451, 452, 453, 454, 455, 456, 458, 463, 464, 467, 468, 469, 470, 471, 472, 473, 475, 479, 482, 483, 484, 485, 486, 488, 492, 493, 494, 495, 496, 497, 498, 500, 504, 506, 507], "branches": [[376, 377], [376, 378], [390, 391], [390, 400], [400, 401], [400, 404], [413, 414], [417, 421], [423, 0], [423, 425], [425, 427], [425, 463]]}

import asyncio
from types import SimpleNamespace
import pytest
import inspect

from browser_use.actor.element import Element


class DummyMethod:
    def __init__(self, func):
        self._func = func

    async def __call__(self, params=None, session_id=None):
        result = self._func(params or {}, session_id=session_id)
        if inspect.isawaitable(result):
            result = await result
        return result


class DummyDOM:
    def __init__(self, scroll_func=None, resolve_func=None):
        self.scrollIntoViewIfNeeded = DummyMethod(scroll_func or (lambda p, session_id=None: {}))
        self.resolveNode = DummyMethod(resolve_func or (lambda p, session_id=None: {}))


class DummyRuntime:
    def __init__(self, call_func=None):
        self.callFunctionOn = DummyMethod(call_func or (lambda p, session_id=None: {}))


class DummyInput:
    def __init__(self, dispatch_func=None):
        self._calls = []
        self.dispatchKeyEvent = DummyMethod(self._dispatch if dispatch_func is None else dispatch_func)

    async def _dispatch(self, params=None, session_id=None):
        # record the call with a shallow copy for assertion
        self._calls.append({'params': dict(params or {}), 'session_id': session_id})
        return {}

    @property
    def calls(self):
        return list(self._calls)


class DummyClient:
    def __init__(self, send):
        self.send = send


class DummyBrowserSession:
    def __init__(self, cdp_client):
        self.cdp_client = cdp_client


@pytest.mark.asyncio
async def test_fill_raises_on_missing_objectid(monkeypatch):
    """
    If resolveNode does not return an object with objectId, the method should raise a wrapped Exception.
    """
    # resolveNode returns a dict without 'object'
    dom = DummyDOM(resolve_func=lambda params, session_id=None: {})
    runtime = DummyRuntime()
    input_ = DummyInput()
    client = DummyClient(SimpleNamespace(DOM=dom, Runtime=runtime, Input=input_))
    browser_session = DummyBrowserSession(client)

    elem = Element(browser_session=browser_session, backend_node_id=123, session_id="sess-1")

    # Speed up sleep to avoid delays
    async def fast_sleep(delay):
        return None
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    with pytest.raises(Exception) as excinfo:
        await elem.fill("hello", clear=True)
    assert "Failed to fill element: Failed to get object ID for element" in str(excinfo.value)


@pytest.mark.asyncio
async def test_fill_requires_session_id_after_bounds(monkeypatch):
    """
    If bounds are obtained but session_id is None, should raise wrapped Exception indicating session id required.
    Also exercise scroll exception branch.
    """
    # scrollIntoViewIfNeeded raises to exercise the except logging path
    def scroll_raise(params, session_id=None):
        raise RuntimeError("scroll failed")

    # resolveNode returns object with objectId
    def resolve_ok(params, session_id=None):
        return {'object': {'objectId': 'obj-1'}}

    # callFunctionOn returns bounding rect to set input_coordinates
    def bounds_ok(params, session_id=None):
        return {'result': {'value': {'x': 10, 'y': 20, 'width': 30, 'height': 40}}}

    dom = DummyDOM(scroll_func=scroll_raise, resolve_func=resolve_ok)
    runtime = DummyRuntime(call_func=bounds_ok)
    input_ = DummyInput()
    client = DummyClient(SimpleNamespace(DOM=dom, Runtime=runtime, Input=input_))
    browser_session = DummyBrowserSession(client)

    # session_id is None to trigger the session_id check after bounds retrieval
    elem = Element(browser_session=browser_session, backend_node_id=456, session_id=None)

    # Speed up sleep
    async def fast_sleep(delay):
        return None
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    with pytest.raises(Exception) as excinfo:
        await elem.fill("x", clear=False)
    assert "Failed to fill element: Session ID is required for fill operation" in str(excinfo.value)


@pytest.mark.asyncio
async def test_fill_types_characters_and_newline(monkeypatch):
    """
    Exercise the normal character typing branch and the newline branch, verifying correct dispatchKeyEvent calls.
    """
    # resolveNode returns object id
    def resolve_ok(params, session_id=None):
        return {'object': {'objectId': 'obj-2'}}

    # callFunctionOn returns nothing useful (no bounding box)
    def bounds_none(params, session_id=None):
        return {}  # no 'result' -> skip bounds path

    dom = DummyDOM(resolve_func=resolve_ok)
    runtime = DummyRuntime(call_func=bounds_none)
    input_ = DummyInput()
    client = DummyClient(SimpleNamespace(DOM=dom, Runtime=runtime, Input=input_))
    browser_session = DummyBrowserSession(client)

    elem = Element(browser_session=browser_session, backend_node_id=789, session_id="sess-2")

    # Patch element helper methods to controlled behavior
    async def focus_stub(backend_node_id, object_id, cdp_client, session_id, input_coordinates=None):
        return True

    async def clear_stub(object_id, cdp_client, session_id):
        return True

    def get_modifiers_and_vk(char):
        # return modifiers=0, vk_code=65 (A), base_key lowercase char
        return (0, 65, char.lower())

    def get_key_code(char):
        return "Key" + char.upper()

    monkeypatch.setattr(elem, "_focus_element_simple", focus_stub)
    monkeypatch.setattr(elem, "_clear_text_field", clear_stub)
    monkeypatch.setattr(elem, "_get_char_modifiers_and_vk", get_modifiers_and_vk)
    monkeypatch.setattr(elem, "_get_key_code_for_char", get_key_code)

    # Speed up sleeps used in the typing loop
    async def fast_sleep(delay):
        return None
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # Call fill with a regular char then newline to trigger both branches
    await elem.fill("a\n")

    # Inspect recorded Input.dispatchKeyEvent calls
    calls = input_.calls
    # Expect sequence:
    # For 'a':
    #   keyDown (type 'keyDown', key base_key 'a', code 'KeyA', modifiers 0, windowsVirtualKeyCode 65)
    #   char (type 'char', text 'a', key 'a')
    #   keyUp (type 'keyUp', key 'a', code 'KeyA', modifiers 0, windowsVirtualKeyCode 65)
    # For '\n':
    #   keyDown (type 'keyDown', key 'Enter' ...)
    #   char (type 'char', text '\r', key 'Enter')
    #   keyUp (type 'keyUp', key 'Enter' ...)
    # Validate ordering and key fields
    assert len(calls) == 6

    # First 3 calls correspond to 'a'
    first = calls[0]['params']
    assert first['type'] == 'keyDown'
    assert first['key'] == 'a'
    assert first['code'] == 'KeyA'
    assert first['modifiers'] == 0
    assert first['windowsVirtualKeyCode'] == 65

    second = calls[1]['params']
    assert second['type'] == 'char'
    assert second['text'] == 'a'
    assert second['key'] == 'a'

    third = calls[2]['params']
    assert third['type'] == 'keyUp'
    assert third['key'] == 'a'
    assert third['code'] == 'KeyA'
    assert third['modifiers'] == 0
    assert third['windowsVirtualKeyCode'] == 65

    # Next three correspond to newline Enter sequence
    fourth = calls[3]['params']
    assert fourth['type'] == 'keyDown'
    assert fourth['key'] == 'Enter'
    assert fourth['code'] == 'Enter'
    assert fourth['windowsVirtualKeyCode'] == 13

    fifth = calls[4]['params']
    assert fifth['type'] == 'char'
    assert fifth['text'] == '\r'
    assert fifth['key'] == 'Enter'

    sixth = calls[5]['params']
    assert sixth['type'] == 'keyUp'
    assert sixth['key'] == 'Enter'
    assert sixth['code'] == 'Enter'
    assert sixth['windowsVirtualKeyCode'] == 13
