# file: browser_use/dom/service.py:385-660
# asked: {"lines": [386, 389, 390, 391, 393, 394, 396, 399, 400, 401, 402, 403, 404, 424, 426, 428, 429, 430, 431, 432, 434, 435, 436, 443, 444, 445, 447, 448, 449, 480, 481, 483, 486, 487, 489, 490, 491, 492, 494, 498, 499, 501, 502, 503, 504, 505, 506, 507, 510, 511, 512, 513, 514, 516, 517, 518, 521, 522, 525, 526, 527, 528, 530, 531, 533, 534, 535, 536, 539, 540, 541, 543, 544, 545, 546, 548, 551, 552, 553, 556, 559, 560, 561, 562, 563, 567, 570, 571, 572, 575, 576, 577, 578, 579, 581, 582, 587, 588, 589, 592, 594, 595, 596, 599, 600, 601, 602, 603, 604, 605, 606, 607, 609, 610, 613, 614, 616, 617, 618, 619, 620, 621, 624, 627, 628, 630, 631, 632, 634, 636, 637, 639, 640, 641, 642, 645, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 659], "branches": [[428, 429], [428, 436], [430, 431], [430, 436], [487, 489], [487, 536], [499, 501], [499, 510], [502, 499], [502, 503], [504, 499], [504, 505], [506, 499], [506, 507], [570, 571], [570, 599], [571, 572], [571, 575], [587, 588], [587, 592], [588, 587], [588, 589], [594, 595], [594, 599], [595, 596], [595, 599], [601, 602], [601, 613], [602, 603], [602, 609], [613, 614], [613, 616], [627, 628], [627, 645], [630, 631], [630, 636], [639, 640], [639, 645], [640, 639], [640, 641]]}
# gained: {"lines": [386, 389, 390, 391, 393, 394, 396, 399, 400, 401, 402, 403, 404, 424, 426, 428, 429, 430, 431, 432, 434, 435, 436, 443, 444, 445, 447, 448, 449, 480, 481, 483, 486, 487, 489, 490, 491, 492, 494, 498, 499, 501, 502, 503, 504, 505, 506, 507, 510, 511, 512, 513, 514, 516, 521, 522, 525, 526, 527, 528, 530, 531, 533, 536, 539, 540, 541, 543, 544, 545, 546, 548, 551, 552, 553, 556, 559, 560, 561, 562, 563, 567, 570, 599, 600, 601, 602, 603, 604, 613, 616, 617, 618, 619, 620, 621, 624, 627, 628, 630, 636, 637, 639, 640, 641, 642, 645, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 659], "branches": [[428, 429], [430, 431], [430, 436], [487, 489], [487, 536], [499, 501], [499, 510], [502, 499], [502, 503], [504, 505], [506, 507], [570, 599], [601, 602], [601, 613], [602, 603], [613, 616], [627, 628], [630, 636], [639, 640], [639, 645], [640, 639], [640, 641]]}

import asyncio
import types
import pytest

import browser_use.dom.service as service_module
from browser_use.dom.service import DomService
from browser_use.dom.views import TargetAllTrees


class DummyLogger:
    def __init__(self):
        self.debug_messages = []
        self.warning_messages = []

    def debug(self, msg):
        self.debug_messages.append(msg)

    def warning(self, msg):
        self.warning_messages.append(msg)


class FakeCDPSend:
    def __init__(self, behavior):
        """
        behavior: dict controlling responses for different calls
        Keys that may be used:
         - ready_state_raises (bool)
         - scroll_result (dict or Exception)
         - js_listener_object_id (str or None)
         - get_properties_result (list)
         - describe_node_map (dict mapping objectId->backendNodeId)
         - release_object_raises (bool)
         - snapshot (dict)
         - dom_tree (dict)
        """
        self.behavior = behavior

        # create nested namespaces: Runtime, DOM, DOMSnapshot
        self.Runtime = types.SimpleNamespace()
        self.DOM = types.SimpleNamespace()
        self.DOMSnapshot = types.SimpleNamespace()

        async def runtime_evaluate(params=None, session_id=None):
            expr = (params or {}).get("expression", "")
            # readyState evaluate is a simple expression equal to 'document.readyState'
            if expr.strip() == "document.readyState":
                if self.behavior.get("ready_state_raises"):
                    raise Exception("ready state error")
                return {"result": {"value": "complete"}}
            # scroll detection expression contains 'iframe' and returns by value
            if "document.querySelectorAll('iframe')" in expr:
                val = self.behavior.get("scroll_result", {})
                if isinstance(val, Exception):
                    raise val
                return {"result": {"value": val}}
            # js listener detection expression contains 'getEventListeners'
            if "getEventListeners" in expr:
                obj_id = self.behavior.get("js_listener_object_id")
                if obj_id is None:
                    # return no objectId
                    return {"result": {}}
                return {"result": {"objectId": obj_id}}
            # Fallback
            return {"result": {"value": None}}

        async def runtime_get_properties(params=None, session_id=None):
            # return the configured get_properties_result
            return {"result": self.behavior.get("get_properties_result", [])}

        async def runtime_release_object(params=None, session_id=None):
            if self.behavior.get("release_object_raises"):
                raise Exception("release failed")
            return {}

        async def dom_describe_node(params=None, session_id=None):
            object_id = (params or {}).get("objectId")
            mapping = self.behavior.get("describe_node_map", {})
            node = {}
            if object_id in mapping:
                node = {"backendNodeId": mapping[object_id]}
            return {"node": node}

        async def domsnapshot_capture_snapshot(params=None, session_id=None):
            return self.behavior.get("snapshot", {"documents": []})

        async def dom_get_document(params=None, session_id=None):
            return self.behavior.get("dom_tree", {})

        # Bind methods
        self.Runtime.evaluate = runtime_evaluate
        self.Runtime.getProperties = runtime_get_properties
        self.Runtime.releaseObject = runtime_release_object
        self.DOM.describeNode = dom_describe_node
        self.DOMSnapshot.captureSnapshot = domsnapshot_capture_snapshot
        self.DOM.getDocument = dom_get_document


class FakeCDPSession:
    def __init__(self, send_obj, session_id="session-1"):
        # cdp_client.send.RUNTIME... is how code calls it
        self.cdp_client = types.SimpleNamespace(send=send_obj)
        self.session_id = session_id


@pytest.mark.asyncio
async def test_get_all_trees_basic_path(monkeypatch):
    # Prepare fake browser_session and DomService instance
    fake_logger = DummyLogger()
    # prepare fake cdp send behavior for the basic path
    behavior = {
        "ready_state_raises": False,
        "scroll_result": {"0": {"scrollTop": 10, "scrollLeft": 20}},
        "js_listener_object_id": None,  # no js listeners object returned
        "snapshot": {
            "documents": [
                {"nodes": [1, 2, 3]},
                {"nodes": [], "frameId": "f1", "url": "u1"},
            ]
        },
        "dom_tree": {"root": "dom"},
    }
    fake_send = FakeCDPSend(behavior)
    fake_session = FakeCDPSession(fake_send)

    async def fake_get_or_create_cdp_session(target_id, focus=False):
        return fake_session

    fake_browser_session = types.SimpleNamespace(get_or_create_cdp_session=fake_get_or_create_cdp_session, logger=fake_logger)

    ds = DomService(browser_session=fake_browser_session)

    # monkeypatch create_task_with_error_handling to just wrap coroutine into a Task
    monkeypatch.setattr(service_module, "create_task_with_error_handling", lambda coro, name=None: asyncio.create_task(coro))

    # stub out _get_ax_tree_for_all_frames and _get_viewport_ratio to simple coroutines
    async def fake_ax_tree(target_id):
        return {"ax": "tree"}

    async def fake_viewport_ratio(target_id):
        return 2.0

    ds._get_ax_tree_for_all_frames = fake_ax_tree
    ds._get_viewport_ratio = fake_viewport_ratio

    # call the method
    result = await ds._get_all_trees("target-1")

    # Assertions: result is TargetAllTrees-like
    assert isinstance(result, TargetAllTrees)
    # Snapshot should have been limited to first document because default max_iframes is large;
    # we set max_iframes to default; to trigger limiting behavior set to 1 before calling
    # But here we assert that snapshot exists and has documents
    assert result.snapshot is not None
    assert isinstance(result.snapshot, dict)
    assert "documents" in result.snapshot
    # dom_tree and ax_tree and device_pixel_ratio returned
    assert result.dom_tree == {"root": "dom"}
    assert result.ax_tree == {"ax": "tree"}
    assert result.device_pixel_ratio == 2.0
    # js_click_listener_backend_ids should be None because none found
    assert result.js_click_listener_backend_ids is None
    # timing keys exist and are numeric
    for k in ("iframe_scroll_detection_ms", "js_listener_detection_ms", "cdp_parallel_calls_ms", "snapshot_processing_ms"):
        assert k in result.cdp_timing
        assert isinstance(result.cdp_timing[k], float) or isinstance(result.cdp_timing[k], (int,))


@pytest.mark.asyncio
async def test_get_all_trees_js_listeners_and_release_error(monkeypatch):
    # This test will exercise:
    # - ready_state evaluate raising (caught)
    # - scroll evaluate raising (caught)
    # - js listener detection returning an objectId, getProperties returning array props,
    #   DOM.describeNode returning backend node id, and Runtime.releaseObject raising
    fake_logger = DummyLogger()
    behavior = {
        "ready_state_raises": True,
        "scroll_result": Exception("scroll failure"),
        "js_listener_object_id": "array-obj-1",
        "get_properties_result": [
            {"name": "0", "value": {"objectId": "elem-1"}},
            {"name": "1", "value": {"objectId": "elem-2"}},
            {"name": "length", "value": 2},
            {"name": "non_numeric", "value": {"objectId": "ignored"}},
        ],
        "describe_node_map": {"elem-1": 101, "elem-2": 102},
        "release_object_raises": True,  # will exercise the except-pass branch
        "snapshot": {"documents": [{"nodes": [1]}]},
        "dom_tree": {"root": "dom2"},
    }
    fake_send = FakeCDPSend(behavior)
    fake_session = FakeCDPSession(fake_send)

    async def fake_get_or_create_cdp_session(target_id, focus=False):
        return fake_session

    fake_browser_session = types.SimpleNamespace(get_or_create_cdp_session=fake_get_or_create_cdp_session, logger=fake_logger)

    ds = DomService(browser_session=fake_browser_session)
    ds.max_iframes = 5

    monkeypatch.setattr(service_module, "create_task_with_error_handling", lambda coro, name=None: asyncio.create_task(coro))

    async def fake_ax_tree(target_id):
        return {"ax": "tree2"}

    async def fake_viewport_ratio(target_id):
        return 1.5

    ds._get_ax_tree_for_all_frames = fake_ax_tree
    ds._get_viewport_ratio = fake_viewport_ratio

    result = await ds._get_all_trees("target-2")

    # result should include backend ids 101 and 102
    assert isinstance(result, TargetAllTrees)
    assert result.js_click_listener_backend_ids == {101, 102}
    # snapshot/documents present
    assert len(result.snapshot["documents"]) == 1
    # dom and ax returned
    assert result.dom_tree == {"root": "dom2"}
    assert result.ax_tree == {"ax": "tree2"}
    assert result.device_pixel_ratio == 1.5
    # Because ready_state_raises was True and scroll_result was exception, ensure those didn't prevent completion
    # and logger captured debug messages
    assert any("Capturing DOM snapshot" in m for m in ds.logger.debug_messages)
