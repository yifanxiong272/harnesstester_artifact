import asyncio
from types import SimpleNamespace
import pytest

import browser_use.browser.session as session_mod


class FakeDOMRect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __eq__(self, other):
        return (
            isinstance(other, FakeDOMRect)
            and self.x == other.x
            and self.y == other.y
            and self.width == other.width
            and self.height == other.height
        )


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        # keep deterministic, store message
        self.messages.append(str(msg))


class DummySelf:
    def __init__(self):
        self.logger = DummyLogger()


class CDPClientSendStub:
    def __init__(self, content_quads_result=None, box_model_result=None, resolve_result=None, js_result=None,
                 raise_content=False, raise_box=False, raise_resolve=False, raise_js=False):
        # set up nested send.DOM and send.Runtime objects with async methods
        dom = SimpleNamespace()
        runtime = SimpleNamespace()

        async def getContentQuads(params=None, session_id=None):
            if raise_content:
                raise Exception("content_quads error")
            return content_quads_result or {}

        async def getBoxModel(params=None, session_id=None):
            if raise_box:
                raise Exception("box_model error")
            return box_model_result or {}

        async def resolveNode(params=None, session_id=None):
            if raise_resolve:
                raise Exception("resolve error")
            return resolve_result or {}

        async def callFunctionOn(params=None, session_id=None):
            if raise_js:
                raise Exception("js error")
            return js_result or {}

        dom.getContentQuads = getContentQuads
        dom.getBoxModel = getBoxModel
        runtime.callFunctionOn = callFunctionOn
        # resolveNode lives under DOM.resolveNode in the real code
        dom.resolveNode = resolveNode

        self.DOM = dom
        self.Runtime = runtime


class CDPClientStub:
    def __init__(self, send_stub: CDPClientSendStub):
        self.send = SimpleNamespace(DOM=send_stub.DOM, Runtime=send_stub.Runtime)


class CDPSessionStub:
    def __init__(self, send_stub: CDPClientSendStub, session_id="session-1"):
        self.session_id = session_id
        self.cdp_client = CDPClientStub(send_stub)


@pytest.fixture(autouse=True)
def patch_domrect(monkeypatch):
    # Patch the DOMRect symbol where the code under test resolves it
    monkeypatch.setattr(session_mod, "DOMRect", FakeDOMRect)


@pytest.mark.asyncio
async def test_get_element_coordinates_content_quads_round_034():
    """When DOM.getContentQuads returns a valid quad, it should be converted to DOMRect."""
    # Build a quad that yields min_x=1, min_y=2, max_x=5, max_y=6 -> width=4 height=4
    quad = [1, 2, 5, 2, 5, 6, 1, 6]
    send_stub = CDPClientSendStub(content_quads_result={"quads": [quad]})
    cdp_session = CDPSessionStub(send_stub)

    dummy = DummySelf()
    # Bind the async method to dummy and call
    func = session_mod.BrowserSession.get_element_coordinates.__get__(dummy, session_mod.BrowserSession)
    rect = await func(backend_node_id=123, cdp_session=cdp_session)

    assert isinstance(rect, FakeDOMRect)
    assert rect.x == 1 and rect.y == 2 and rect.width == 4 and rect.height == 4
    # ensure we logged the success from getContentQuads path
    assert any("Got 1 quads" in m or "Got 1 quads" in m for m in dummy.logger.messages) or dummy.logger.messages


@pytest.mark.asyncio
async def test_get_element_coordinates_box_model_fallback_round_034():
    """When getContentQuads yields no quads, DOM.getBoxModel content should be used to create a quad."""
    # getContentQuads returns empty -> fallback to getBoxModel
    content_quads = {"quads": []}
    # give content with 8 numbers representing points -> box->content
    content_quad = [10, 20, 30, 20, 30, 40, 10, 40]
    box_model = {"model": {"content": content_quad}}
    send_stub = CDPClientSendStub(content_quads_result=content_quads, box_model_result=box_model)
    cdp_session = CDPSessionStub(send_stub)

    dummy = DummySelf()
    func = session_mod.BrowserSession.get_element_coordinates.__get__(dummy, session_mod.BrowserSession)
    rect = await func(backend_node_id=5, cdp_session=cdp_session)

    # From the content_quad, min_x=10, min_y=20, max_x=30, max_y=40 -> width=20 height=20
    assert isinstance(rect, FakeDOMRect)
    assert rect == FakeDOMRect(10, 20, 20, 20)
    # ensure debug message about box model path was recorded
    assert any("Got quad from DOM.getBoxModel" in m for m in dummy.logger.messages) or dummy.logger.messages


@pytest.mark.asyncio
async def test_get_element_coordinates_js_fallback_success_round_034():
    """When both DOM methods fail or provide no data, JS getBoundingClientRect returning positive size yields a DOMRect."""
    # Both DOM methods return empty dicts -> fall through to resolveNode + Runtime.callFunctionOn
    resolve_result = {"object": {"objectId": "obj-1"}}
    js_value = {"x": 7, "y": 8, "width": 9, "height": 10}
    js_result = {"result": {"value": js_value}}

    send_stub = CDPClientSendStub(content_quads_result={}, box_model_result={}, resolve_result=resolve_result, js_result=js_result)
    cdp_session = CDPSessionStub(send_stub)

    dummy = DummySelf()
    func = session_mod.BrowserSession.get_element_coordinates.__get__(dummy, session_mod.BrowserSession)
    rect = await func(backend_node_id=9, cdp_session=cdp_session)

    assert isinstance(rect, FakeDOMRect)
    assert rect == FakeDOMRect(7, 8, 9, 10)
    # confirm we hit the JS path by presence of no quads and our returned rect
    assert rect.width == 9 and rect.height == 10


@pytest.mark.asyncio
async def test_get_element_coordinates_js_fallback_zero_dimension_round_034():
    """When JS getBoundingClientRect returns a zero width (or height), it should not return a DOMRect (None expected)."""
    resolve_result = {"object": {"objectId": "obj-2"}}
    # width is zero -> should not return from JS path
    js_value = {"x": 0, "y": 0, "width": 0, "height": 5}
    js_result = {"result": {"value": js_value}}

    send_stub = CDPClientSendStub(content_quads_result={}, box_model_result={}, resolve_result=resolve_result, js_result=js_result)
    cdp_session = CDPSessionStub(send_stub)

    dummy = DummySelf()
    func = session_mod.BrowserSession.get_element_coordinates.__get__(dummy, session_mod.BrowserSession)
    rect = await func(backend_node_id=77, cdp_session=cdp_session)

    assert rect is None
    # logger should have an entry about JS path attempt or the subsequent lack of quads
    assert dummy.logger.messages
