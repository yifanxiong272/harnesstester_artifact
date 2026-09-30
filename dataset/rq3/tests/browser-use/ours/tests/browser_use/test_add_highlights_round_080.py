import asyncio
from types import SimpleNamespace
from pprint import pformat
import pytest

from browser_use.browser.session import BrowserSession


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.warn_msgs = []

    def debug(self, *args, **kwargs):
        # Record joined representation for easy assertions
        self.debug_msgs.append(" ".join(str(a) for a in args))

    def warning(self, *args, **kwargs):
        self.warn_msgs.append(" ".join(str(a) for a in args))


class Rect:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class SnapshotNode:
    def __init__(self, is_clickable=True):
        self.is_clickable = is_clickable


class NodeWithChildrenText:
    def __init__(self, **kwargs):
        # Accept and set arbitrary attributes used by add_highlights
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_all_children_text(self):
        return "child-text-value"


class NodeWithNodeValue:
    def __init__(self, node_value, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.node_value = node_value


async def _noop_async(*_, **__):
    return None


def make_cdp_session(return_value):
    """Create a fake cdp_session whose cdp_client.send.Runtime.evaluate returns return_value."""
    async def evaluate(params=None, session_id=None):
        return return_value

    Runtime = SimpleNamespace(evaluate=evaluate)
    send = SimpleNamespace(Runtime=Runtime)
    cdp_client = SimpleNamespace(send=send)
    return SimpleNamespace(cdp_client=cdp_client, session_id="fake-session")


def make_base_self(dom_highlight_elements=True):
    """Construct a minimal self object compatible with BrowserSession.add_highlights."""
    browser_profile = SimpleNamespace(dom_highlight_elements=dom_highlight_elements)
    logger = DummyLogger()
    # remove_highlights & get_or_create_cdp_session will be replaced per-test as needed
    base = SimpleNamespace(
        browser_profile=browser_profile,
        logger=logger,
        remove_highlights=_noop_async,
        get_or_create_cdp_session=lambda: (_ for _ in ()).throw(RuntimeError("should be replaced")),
    )
    return base


def run_async(coro):
    """Helper to run async coroutines deterministically in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def test_early_return_when_dom_highlight_disabled_round_080():
    """If dom_highlight_elements is falsy, the function should return early and not call CDP."""
    self_obj = make_base_self(dom_highlight_elements=False)

    # Provide a selector_map that would normally produce elements
    node = NodeWithNodeValue(node_value="value", absolute_position=Rect(1, 2, 10, 10),
                             node_name="div", snapshot_node=SnapshotNode(False),
                             attributes={"a": "b"}, node_id=1, backend_node_id="bn1",
                             xpath="/html/body/div")
    selector_map = {0: node}

    # Call the coroutine - should return quickly
    run_async(BrowserSession.add_highlights(self_obj, selector_map))

    # Ensure nothing was logged to indicate injection or errors
    assert any('No valid elements to highlight' in msg for msg in self_obj.logger.debug_msgs) is False
    assert any('Creating highlights' in msg for msg in self_obj.logger.debug_msgs) is False


def test_no_valid_bboxes_logs_and_returns_round_080():
    """Elements with zero width/height are ignored; if none remain, function logs and returns."""
    self_obj = make_base_self(dom_highlight_elements=True)

    # Node has absolute_position but zero width -> should be filtered out
    node = NodeWithChildrenText(
        absolute_position=Rect(5, 5, 0, 10),  # width==0 triggers filtering
        node_name="span",
        snapshot_node=None,
        attributes=None,
        node_id=2,
        backend_node_id="bn2",
        xpath="/html/body/span",
        node_value="nv",
    )
    selector_map = {10: node}

    # Ensure remove_highlights and get_or_create_cdp_session are replaced with stubs that would raise if called
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("CDP or remove_highlights should not be called when there are no valid elements")

    self_obj.remove_highlights = fail_if_called
    self_obj.get_or_create_cdp_session = lambda: (_ for _ in ()).throw(AssertionError("should not be called"))

    # Also patch asyncio.sleep to no-op to avoid delays
    original_sleep = asyncio.sleep
    asyncio.sleep = _noop_async
    try:
        run_async(BrowserSession.add_highlights(self_obj, selector_map))
    finally:
        asyncio.sleep = original_sleep

    # The logger should have recorded the 'No valid elements to highlight' debug message
    assert any('No valid elements to highlight' in msg for msg in self_obj.logger.debug_msgs)


def test_evaluate_returns_added_and_missing_value_branches_round_080():
    """Cover both branches where Runtime.evaluate returns a value with 'added' and where it lacks expected fields."""
    # First: case where evaluate returns the expected nested result with added count
    self_obj1 = make_base_self(dom_highlight_elements=True)

    # Good bbox -> will be included
    node1 = NodeWithChildrenText(
        absolute_position=Rect(0, 0, 20, 30),
        node_name="button",
        snapshot_node=SnapshotNode(is_clickable=False),
        is_scrollable=True,
        attributes={"role": "btn"},
        frame_id="frame-1",
        node_id=3,
        backend_node_id="bn3",
        xpath="/html/body/button",
    )
    selector_map1 = {1: node1}

    # Patch remove_highlights and get_or_create_cdp_session
    self_obj1.remove_highlights = _noop_async
    res_with_added = {"result": {"value": {"added": 1}}}
    async def get_cdp_session1():
        return make_cdp_session(res_with_added)
    self_obj1.get_or_create_cdp_session = get_cdp_session1

    # Patch asyncio.sleep to no-op
    orig_sleep = asyncio.sleep
    asyncio.sleep = _noop_async
    try:
        run_async(BrowserSession.add_highlights(self_obj1, selector_map1))
    finally:
        asyncio.sleep = orig_sleep

    # Assert that the success path with added count was logged
    assert any('Successfully added 1 highlight' in msg or 'Successfully added 1 highlight elements' in msg or 'Successfully added' in msg for msg in self_obj1.logger.debug_msgs)

    # Second: case where evaluate returns a dict missing nested 'result'/'value' -> hits else branch
    self_obj2 = make_base_self(dom_highlight_elements=True)
    node2 = NodeWithNodeValue(node_value="rawtext", absolute_position=Rect(1, 1, 10, 10),
                               node_name="p", snapshot_node=None,
                               attributes=None, node_id=4, backend_node_id="bn4", xpath="/p")
    selector_map2 = {5: node2}
    self_obj2.remove_highlights = _noop_async
    # Return an empty dict (no 'result' key)
    res_missing = {}
    async def get_cdp_session2():
        return make_cdp_session(res_missing)
    self_obj2.get_or_create_cdp_session = get_cdp_session2

    # Patch asyncio.sleep again
    orig_sleep = asyncio.sleep
    asyncio.sleep = _noop_async
    try:
        run_async(BrowserSession.add_highlights(self_obj2, selector_map2))
    finally:
        asyncio.sleep = orig_sleep

    # Should have logged the fallback debug message indicating injection completed
    assert any('Browser highlight injection completed' in msg for msg in self_obj2.logger.debug_msgs)
