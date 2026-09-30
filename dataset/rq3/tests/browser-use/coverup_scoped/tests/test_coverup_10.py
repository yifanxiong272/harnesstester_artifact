# file: browser_use/browser/session.py:2369-2478
# asked: {"lines": [2383, 2386, 2387, 2388, 2391, 2393, 2395, 2396, 2397, 2398, 2399, 2400, 2402, 2405, 2406, 2407, 2408, 2411, 2412, 2413, 2414, 2415, 2418, 2419, 2420, 2421, 2423, 2424, 2427, 2428, 2430, 2431, 2432, 2433, 2434, 2435, 2436, 2437, 2438, 2439, 2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449, 2451, 2452, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2476, 2477, 2478], "branches": [[2387, 2388], [2387, 2391], [2406, 2407], [2406, 2411], [2411, 2412], [2411, 2418], [2412, 2413], [2412, 2418], [2413, 2412], [2413, 2414]]}
# gained: {"lines": [2383, 2386, 2387, 2388, 2391, 2393, 2395, 2396, 2397, 2398, 2399, 2400, 2402, 2405, 2406, 2407, 2408, 2411, 2412, 2413, 2414, 2415, 2418, 2419, 2420, 2421, 2423, 2424, 2427, 2428, 2430, 2431, 2432, 2433, 2434, 2435, 2436, 2437, 2438, 2439, 2440, 2441, 2442, 2443, 2444, 2445, 2446, 2447, 2448, 2449, 2451, 2452, 2454, 2455, 2456, 2457, 2458, 2459, 2460, 2461, 2462, 2463, 2464, 2465, 2466, 2467, 2468, 2469, 2470, 2471, 2472, 2473, 2476, 2477, 2478], "branches": [[2387, 2388], [2387, 2391], [2406, 2407], [2406, 2411], [2411, 2412], [2411, 2418], [2412, 2413], [2413, 2414]]}

import pytest
import asyncio

from browser_use.browser.session import BrowserSession
from browser_use.dom.views import EnhancedDOMTreeNode, NodeType


class FakeDOM:
    def __init__(self, get_node_ret=None, describe_ret=None, get_node_exc=None, describe_exc=None):
        self._get_node_ret = get_node_ret
        self._describe_ret = describe_ret
        self._get_node_exc = get_node_exc
        self._describe_exc = describe_exc

    async def getNodeForLocation(self, params=None, session_id=None):
        if self._get_node_exc:
            raise self._get_node_exc
        return self._get_node_ret

    async def describeNode(self, params=None, session_id=None):
        if self._describe_exc:
            raise self._describe_exc
        return self._describe_ret


class FakeSend:
    def __init__(self, dom: FakeDOM):
        self.DOM = dom


class FakeClient:
    def __init__(self, dom: FakeDOM):
        self.send = FakeSend(dom)


class FakePage:
    def __init__(self, session_id: str = "session-1"):
        self._session_id = session_id

    async def _ensure_session(self):
        return self._session_id


@pytest.mark.asyncio
async def test_no_active_page_raises(monkeypatch):
    session = BrowserSession()

    async def _none_page(self):
        return None

    # patch the class method so pydantic model assignment isn't triggered
    monkeypatch.setattr(BrowserSession, "get_current_page", _none_page)

    with pytest.raises(RuntimeError):
        await session.get_dom_element_at_coordinates(10, 20)


@pytest.mark.asyncio
async def test_get_node_for_location_no_backend_node_returns_none(monkeypatch):
    session = BrowserSession()
    page = FakePage(session_id="s1")

    async def _page(self):
        return page

    monkeypatch.setattr(BrowserSession, "get_current_page", _page)

    dom = FakeDOM(get_node_ret={"nodeId": 1, "frameId": "f1"})  # no backendNodeId
    client = FakeClient(dom)
    session._cdp_client_root = client

    result = await session.get_dom_element_at_coordinates(1, 2)
    assert result is None


@pytest.mark.asyncio
async def test_found_in_cached_selector_map_returns_cached_node(monkeypatch):
    session = BrowserSession()
    page = FakePage(session_id="sess-2")

    async def _page(self):
        return page

    monkeypatch.setattr(BrowserSession, "get_current_page", _page)

    backend_id = 555
    dom = FakeDOM(get_node_ret={"backendNodeId": backend_id, "nodeId": 99, "frameId": "frame-x"})
    client = FakeClient(dom)
    session._cdp_client_root = client

    node = EnhancedDOMTreeNode(
        node_id=99,
        backend_node_id=backend_id,
        node_type=NodeType.ELEMENT_NODE,
        node_name="DIV",
        node_value="",
        attributes={},
        is_scrollable=None,
        is_visible=None,
        absolute_position=None,
        target_id="t",
        frame_id="frame-x",
        session_id="sess-2",
        content_document=None,
        shadow_root_type=None,
        shadow_roots=None,
        parent_node=None,
        children_nodes=None,
        ax_node=None,
        snapshot_node=None,
    )
    # populate cached selector map with the node
    session._cached_selector_map = {1: node}

    result = await session.get_dom_element_at_coordinates(5, 6)
    assert result is node


@pytest.mark.asyncio
async def test_describe_node_success_parses_attributes_and_fields(monkeypatch):
    session = BrowserSession()
    page = FakePage(session_id="sess-3")

    async def _page(self):
        return page

    monkeypatch.setattr(BrowserSession, "get_current_page", _page)

    backend_id = 777
    get_node_ret = {"backendNodeId": backend_id, "nodeId": 123, "frameId": "frame-7"}
    # describeNode returns a node dict with attributes as flat list
    describe_ret = {
        "node": {
            "nodeName": "SPAN",
            "nodeType": NodeType.ELEMENT_NODE.value,
            "nodeValue": "some value",
            "attributes": ["id", "elem-1", "class", "a b"]
        }
    }
    dom = FakeDOM(get_node_ret=get_node_ret, describe_ret=describe_ret)
    client = FakeClient(dom)
    session._cdp_client_root = client

    # ensure cached selector map empty so code falls back to describeNode
    session._cached_selector_map = {}

    node = await session.get_dom_element_at_coordinates(11, 22)
    assert isinstance(node, EnhancedDOMTreeNode)
    assert node.backend_node_id == backend_id
    assert node.node_id == 123
    assert node.node_name == "SPAN"
    assert node.node_value == "some value"
    assert node.attributes == {"id": "elem-1", "class": "a b"}
    assert node.frame_id == "frame-7"
    assert node.session_id == "sess-3"


@pytest.mark.asyncio
async def test_describe_node_failure_returns_minimal_node(monkeypatch):
    session = BrowserSession()
    page = FakePage(session_id="sess-4")

    async def _page(self):
        return page

    monkeypatch.setattr(BrowserSession, "get_current_page", _page)

    backend_id = 888
    get_node_ret = {"backendNodeId": backend_id, "nodeId": 222, "frameId": "frame-8"}
    dom = FakeDOM(get_node_ret=get_node_ret, describe_exc=Exception("describe-failed"))
    client = FakeClient(dom)
    session._cdp_client_root = client

    session._cached_selector_map = {}

    node = await session.get_dom_element_at_coordinates(0, 0)
    assert isinstance(node, EnhancedDOMTreeNode)
    assert node.backend_node_id == backend_id
    # minimal node uses ELEMENT_NODE
    assert node.node_type == NodeType.ELEMENT_NODE
    assert node.node_name == ""
    assert node.node_value == ""
    assert node.attributes == {}
    assert node.node_id == 222
    assert node.frame_id == "frame-8"
    assert node.session_id == "sess-4"


@pytest.mark.asyncio
async def test_get_node_for_location_raises_logs_and_returns_none(monkeypatch):
    session = BrowserSession()
    page = FakePage(session_id="sess-5")

    async def _page(self):
        return page

    monkeypatch.setattr(BrowserSession, "get_current_page", _page)

    dom = FakeDOM(get_node_exc=RuntimeError("cdp-failure"))
    client = FakeClient(dom)
    session._cdp_client_root = client

    result = await session.get_dom_element_at_coordinates(9, 9)
    assert result is None
