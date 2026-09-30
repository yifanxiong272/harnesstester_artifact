import asyncio
import sys
import types
import logging
import pytest
import types as _types
from types import ModuleType
import types as _t
import builtins
import types

# Import the module under test
import browser_use.browser.session as session_mod

# Provide a deterministic, minimal EnhancedDOMTreeNode replacement and NodeType
class DummyEnhancedDOMTreeNode:
    def __init__(self, *, node_id=0, backend_node_id=None, node_type=None, node_name="", node_value="", attributes=None, is_scrollable=None, frame_id=None, session_id=None, target_id=None, content_document=None, shadow_root_type=None, shadow_roots=None, parent_node=None, children_nodes=None, ax_node=None, snapshot_node=None, is_visible=None, absolute_position=None):
        self.node_id = node_id
        self.backend_node_id = backend_node_id
        self.node_type = node_type
        self.node_name = node_name
        self.node_value = node_value
        self.attributes = attributes or {}
        self.is_scrollable = is_scrollable
        self.frame_id = frame_id
        self.session_id = session_id
        self.target_id = target_id
        self.content_document = content_document
        self.shadow_root_type = shadow_root_type
        self.shadow_roots = shadow_roots
        self.parent_node = parent_node
        self.children_nodes = children_nodes
        self.ax_node = ax_node
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self.absolute_position = absolute_position

# Ensure that the session module uses our replacement class so constructions in the code under test succeed
session_mod.EnhancedDOMTreeNode = DummyEnhancedDOMTreeNode

# Create a fake browser_use.dom.views module with NodeType IntEnum-like behavior
# The code inside the method does: from browser_use.dom.views import NodeType
# and later calls NodeType(node_info.get('nodeType', NodeType.ELEMENT_NODE.value))
from enum import IntEnum
class NodeTypeEnum(IntEnum):
    ELEMENT_NODE = 1
    TEXT_NODE = 3

# Inject module into sys.modules so the dynamic import inside the method resolves deterministically
dom_views_mod = ModuleType("browser_use.dom.views")
dom_views_mod.NodeType = NodeTypeEnum
sys.modules["browser_use.dom.views"] = dom_views_mod

# Helper factories for fake page and fake cdp client
class FakeDOMMethods:
    def __init__(self, get_node_result=None, describe_node_result=None, get_node_exc=None, describe_exc=None):
        # configure return values or exceptions
        self._get_node_result = get_node_result
        self._describe_node_result = describe_node_result
        self._get_node_exc = get_node_exc
        self._describe_exc = describe_exc

    async def getNodeForLocation(self, *, params=None, session_id=None):
        if self._get_node_exc:
            raise self._get_node_exc
        # return the configured dict (or empty dict)
        return self._get_node_result or {}

    async def describeNode(self, *, params=None, session_id=None):
        if self._describe_exc:
            raise self._describe_exc
        return self._describe_node_result or {"node": {}}

class FakeCDPSend:
    def __init__(self, dom_methods):
        self.DOM = dom_methods

class FakeCDPClient:
    def __init__(self, dom_methods):
        self.send = FakeCDPSend(dom_methods)

class FakePage:
    def __init__(self, session_id_value="sess"):
        self._session_id_value = session_id_value
        self._ensured = False

    async def _ensure_session(self):
        # mimic an async call that returns a session id
        self._ensured = True
        return self._session_id_value

# Create a small dummy container object to act as 'self' for the bound method
class DummySession:
    def __init__(self):
        self.cdp_client = None
        self._cached_selector_map = {}
        self.agent_focus_target_id = "target-1"
        # simple logger capturing messages so tests can run without external logging config
        self.logger = logging.getLogger(f"DummySession-{id(self)}")
        # ensure logger doesn't propagate to root during tests
        self.logger.propagate = False

    # get_current_page will be set per-test (async function)

# Helper to bind the original method onto our DummySession
import types as _types

def bind_method_to_dummy(dummy: DummySession):
    # Grab the unbound function from the real BrowserSession class
    func = session_mod.BrowserSession.get_dom_element_at_coordinates
    return _types.MethodType(func, dummy)

@pytest.mark.asyncio
async def test_page_none_round_090():
    dummy = DummySession()

    async def no_page():
        return None

    dummy.get_current_page = no_page

    bound = bind_method_to_dummy(dummy)

    with pytest.raises(RuntimeError) as exc:
        await bound(10, 20)
    assert "No active page found" in str(exc.value)

@pytest.mark.asyncio
async def test_no_backend_node_round_090():
    dummy = DummySession()
    page = FakePage()
    async def cur_page():
        return page
    dummy.get_current_page = cur_page

    # getNodeForLocation returns a dict with no 'backendNodeId'
    dom_methods = FakeDOMMethods(get_node_result={"nodeId": 123})
    dummy.cdp_client = FakeCDPClient(dom_methods)

    bound = bind_method_to_dummy(dummy)

    result = await bound(1, 2)
    assert result is None

@pytest.mark.asyncio
async def test_cached_selector_map_hit_round_090():
    dummy = DummySession()
    page = FakePage()
    async def cur_page():
        return page
    dummy.get_current_page = cur_page

    # The CDP reports a backendNodeId; we will put a node in cached_selector_map with that backend id
    backend_id = "bn-xyz"
    dom_methods = FakeDOMMethods(get_node_result={"nodeId": 5, "backendNodeId": backend_id})
    dummy.cdp_client = FakeCDPClient(dom_methods)

    # Create a fake cached node whose backend_node_id attribute matches
    class CachedNode:
        def __init__(self, backend_node_id):
            self.backend_node_id = backend_node_id
    cached_node = CachedNode(backend_id)
    dummy._cached_selector_map = {"k": cached_node}

    bound = bind_method_to_dummy(dummy)

    result = await bound(3, 4)
    # The method should return the exact cached node object
    assert result is cached_node

@pytest.mark.asyncio
async def test_describe_success_round_090():
    dummy = DummySession()
    page = FakePage()
    async def cur_page():
        return page
    dummy.get_current_page = cur_page

    backend_id = "bn-123"
    # getNodeForLocation returns backendNodeId and nodeId/frameId
    get_result = {"nodeId": 10, "backendNodeId": backend_id, "frameId": "frame-9"}

    # describeNode returns a node with attributes as flat list
    describe_result = {
        "node": {
            "nodeName": "DIV",
            "nodeType": 1,
            "nodeValue": "somevalue",
            "attributes": ["id", "myid", "class", "myclass"]
        }
    }

    dom_methods = FakeDOMMethods(get_node_result=get_result, describe_node_result=describe_result)
    dummy.cdp_client = FakeCDPClient(dom_methods)

    bound = bind_method_to_dummy(dummy)

    node = await bound(7, 8)
    # It should return our DummyEnhancedDOMTreeNode instance
    assert isinstance(node, DummyEnhancedDOMTreeNode)
    assert node.backend_node_id == backend_id
    assert node.node_name == "DIV"
    assert node.node_value == "somevalue"
    assert node.attributes == {"id": "myid", "class": "myclass"}
    # Ensure session_id and frame_id were propagated
    assert node.session_id == "sess"
    assert node.frame_id == "frame-9"

@pytest.mark.asyncio
async def test_describe_fails_fallback_round_090():
    dummy = DummySession()
    page = FakePage()
    async def cur_page():
        return page
    dummy.get_current_page = cur_page

    backend_id = "bn-err"
    get_result = {"nodeId": 77, "backendNodeId": backend_id, "frameId": "frame-err"}

    # configure describeNode to raise
    dom_methods = FakeDOMMethods(get_node_result=get_result, describe_exc=RuntimeError("boom"))
    dummy.cdp_client = FakeCDPClient(dom_methods)

    bound = bind_method_to_dummy(dummy)

    node = await bound(11, 12)
    # Should get a fallback DummyEnhancedDOMTreeNode with minimal info
    assert isinstance(node, DummyEnhancedDOMTreeNode)
    assert node.backend_node_id == backend_id
    assert node.node_name == ""
    assert node.attributes == {}
    assert node.node_id == 77

@pytest.mark.asyncio
async def test_getNode_exception_round_090():
    dummy = DummySession()
    page = FakePage()
    async def cur_page():
        return page
    dummy.get_current_page = cur_page

    # configure getNodeForLocation to raise an exception - should be caught and return None
    dom_methods = FakeDOMMethods(get_node_exc=ValueError("cdp fail"))
    dummy.cdp_client = FakeCDPClient(dom_methods)

    bound = bind_method_to_dummy(dummy)

    result = await bound(0, 0)
    assert result is None
