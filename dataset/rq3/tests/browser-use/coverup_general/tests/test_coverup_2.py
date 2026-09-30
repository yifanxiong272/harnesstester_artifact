# file: browser_use/dom/service.py:662-1039
# asked: {"lines": [683, 684, 687, 688, 689, 690, 691, 693, 694, 695, 696, 697, 700, 701, 702, 704, 706, 707, 710, 711, 712, 714, 716, 717, 718, 731, 732, 735, 736, 738, 739, 743, 744, 746, 747, 748, 750, 753, 754, 755, 756, 757, 759, 760, 761, 762, 763, 764, 767, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 787, 788, 789, 790, 791, 792, 793, 796, 797, 798, 799, 801, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 826, 828, 829, 830, 834, 835, 836, 839, 840, 841, 843, 844, 849, 850, 851, 853, 854, 856, 857, 859, 860, 861, 863, 866, 867, 868, 869, 870, 873, 874, 876, 877, 879, 880, 881, 882, 884, 886, 887, 888, 889, 893, 894, 898, 899, 900, 901, 903, 904, 905, 906, 907, 908, 910, 911, 919, 922, 923, 924, 928, 931, 933, 934, 935, 936, 939, 940, 941, 943, 944, 947, 949, 951, 953, 954, 957, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 974, 975, 976, 977, 978, 984, 985, 986, 987, 988, 989, 993, 994, 995, 997, 998, 999, 1000, 1002, 1003, 1005, 1006, 1007, 1008, 1010, 1015, 1016, 1017, 1019, 1022, 1025, 1026, 1029, 1030, 1031, 1032, 1033, 1035, 1036, 1037, 1039], "branches": [[731, 732], [731, 735], [735, 736], [735, 738], [743, 744], [743, 746], [747, 748], [747, 750], [754, 755], [754, 759], [756, 757], [756, 759], [760, 761], [760, 767], [770, 771], [770, 787], [773, 774], [773, 778], [775, 776], [775, 778], [779, 780], [779, 782], [788, 789], [788, 796], [828, 829], [828, 834], [835, 836], [835, 848], [839, 840], [839, 848], [848, 853], [848, 859], [853, 854], [853, 859], [859, 860], [859, 866], [866, 867], [866, 876], [868, 869], [868, 876], [876, 877], [876, 893], [880, 881], [880, 884], [881, 882], [881, 884], [884, 886], [884, 893], [886, 887], [886, 888], [898, 899], [898, 917], [902, 910], [902, 917], [917, 922], [917, 1010], [922, 923], [922, 928], [931, 933], [931, 949], [933, 934], [933, 947], [939, 940], [939, 943], [951, 953], [951, 1010], [953, 954], [953, 957], [963, 964], [963, 974], [965, 966], [965, 974], [967, 968], [967, 974], [969, 967], [969, 970], [975, 976], [975, 993], [977, 978], [977, 993], [993, 994], [993, 1010], [1036, 1037], [1036, 1039]]}
# gained: {"lines": [683, 684, 687, 688, 689, 690, 691, 693, 694, 695, 696, 697, 700, 701, 702, 704, 706, 707, 710, 711, 712, 714, 716, 717, 718, 731, 732, 735, 736, 738, 739, 743, 746, 747, 750, 753, 754, 755, 756, 757, 759, 760, 767, 770, 771, 772, 773, 778, 779, 780, 781, 782, 783, 784, 787, 788, 789, 790, 791, 792, 793, 796, 797, 798, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 826, 828, 834, 835, 849, 850, 851, 853, 854, 856, 857, 859, 866, 876, 877, 879, 880, 884, 886, 888, 889, 893, 894, 898, 899, 900, 901, 903, 910, 911, 919, 922, 928, 931, 933, 934, 935, 936, 939, 940, 941, 951, 953, 954, 957, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 974, 975, 976, 977, 978, 984, 985, 986, 987, 988, 989, 993, 994, 995, 997, 998, 999, 1000, 1002, 1003, 1005, 1006, 1010, 1015, 1016, 1017, 1019, 1022, 1025, 1026, 1029, 1030, 1031, 1032, 1033, 1035, 1036, 1039], "branches": [[731, 732], [731, 735], [735, 736], [735, 738], [743, 746], [747, 750], [754, 755], [754, 759], [756, 757], [756, 759], [760, 767], [770, 771], [770, 787], [773, 778], [779, 780], [788, 789], [788, 796], [828, 834], [835, 848], [848, 853], [848, 859], [853, 854], [859, 866], [866, 876], [876, 877], [876, 893], [880, 884], [884, 886], [884, 893], [886, 888], [898, 899], [898, 917], [902, 910], [917, 922], [917, 1010], [922, 928], [931, 933], [933, 934], [939, 940], [951, 953], [953, 954], [963, 964], [965, 966], [967, 968], [969, 970], [975, 976], [977, 978], [993, 994], [1036, 1039]]}

import asyncio
import logging
from types import SimpleNamespace

import pytest

import browser_use.dom.service as service_module
from browser_use.dom.service import DomService


@pytest.mark.asyncio
async def test_get_dom_tree_interactive_element_without_snapshot(monkeypatch):
    """
    Test that get_dom_tree processes an interactive element (INPUT) when there's no snapshot data,
    exercising the debug-logging branch for missing snapshot and the form-element debug branch
    that looks for 'city/state/zip' in id/name.
    """

    logger = logging.getLogger("test_logger")
    logger.disabled = True

    # Fake browser session and session creation
    class FakeSession:
        def __init__(self):
            self.session_id = "fake-session-1"

    class FakeBrowserSession:
        def __init__(self):
            self.logger = logger
            self.session_manager = SimpleNamespace(get_target=lambda tid: None)

        async def get_or_create_cdp_session(self, target_id, focus=False):
            return FakeSession()

        async def get_all_frames(self):
            return {}, None

    fake_browser_session = FakeBrowserSession()

    # Create a DOM node representing an INPUT with id containing 'city' and without snapshot
    input_node = {
        "nodeId": 1,
        "backendNodeId": 100,
        "nodeType": 1,  # ELEMENT_NODE
        "nodeName": "INPUT",
        "nodeValue": "",
        "attributes": ["id", "city_input", "name", "user_city"],
        "children": [],
    }
    dom_tree = {"root": input_node}
    ax_tree = {"nodes": []}
    snapshot = {}  # will be ignored by our build_snapshot_lookup stub

    # Monkeypatch DomService._get_all_trees to return our controlled trees
    async def fake_get_all_trees(self, target_id):
        return SimpleNamespace(
            cdp_timing={},
            dom_tree=dom_tree,
            ax_tree=ax_tree,
            snapshot=snapshot,
            device_pixel_ratio=1.0,
            js_click_listener_backend_ids=set(),
        )

    monkeypatch.setattr(DomService, "_get_all_trees", fake_get_all_trees)

    # Monkeypatch build_snapshot_lookup to return empty dict to simulate missing snapshot data
    def fake_build_snapshot_lookup(snapshot_obj, device_pixel_ratio):
        return {}  # no snapshot entries

    monkeypatch.setattr(service_module, "build_snapshot_lookup", fake_build_snapshot_lookup)

    dom_service = DomService(fake_browser_session, logger=logger, cross_origin_iframes=False)

    enhanced_node, timing_info = await dom_service.get_dom_tree("target-main")

    # Assertions
    assert enhanced_node is not None
    assert enhanced_node.node_id == 1
    # Attributes should have been parsed into dict form
    assert enhanced_node.attributes.get("id") == "city_input"
    assert enhanced_node.attributes.get("name") == "user_city"
    # Because build_snapshot_lookup returned empty, snapshot_node should be None
    assert enhanced_node.snapshot_node is None
    # is_visible should be a boolean (method computes it)
    assert isinstance(enhanced_node.is_visible, bool)
    # timing_info should contain keys added by function
    assert "get_all_trees_total_ms" in timing_info
    assert "construct_enhanced_tree_ms" in timing_info
    assert "get_dom_tree_total_ms" in timing_info


@pytest.mark.asyncio
async def test_get_dom_tree_cross_origin_iframe_processing(monkeypatch):
    """
    Test processing of a cross-origin iframe when cross_origin_iframes=True.
    This exercises the branch that lazily fetches all_frames, matches iframe by src URL,
    and recursively calls get_dom_tree for the iframe's target.
    """

    logger = logging.getLogger("test_logger2")
    logger.disabled = True

    # Fake browser session, session creation, and session manager
    class FakeSession:
        def __init__(self):
            self.session_id = "fake-session-2"

    class FakeSessionManager:
        def __init__(self, target_map):
            self._map = target_map

        def get_target(self, target_id):
            # Return object representing a real target if present
            return self._map.get(target_id)

    class FakeBrowserSession:
        def __init__(self, target_map, all_frames_map):
            self.logger = logger
            self.session_manager = FakeSessionManager(target_map)
            self._all_frames_map = all_frames_map

        async def get_or_create_cdp_session(self, target_id, focus=False):
            return FakeSession()

        async def get_all_frames(self):
            # Return a tuple (all_frames, something) as expected by the implementation
            return self._all_frames_map, None

    # Prepare two targets: main and iframe target
    MAIN_TARGET = "main-target"
    IFRAME_TARGET_ID = "iframe-target-id"

    # Nodes:
    # Main root has a child iframe element with no contentDocument, but with src attribute.
    iframe_node = {
        "nodeId": 2,
        "backendNodeId": 200,
        "nodeType": 1,
        "nodeName": "IFRAME",
        "nodeValue": "",
        "attributes": ["src", "https://example.com/path?query=1"],
        "children": [],
        # no 'contentDocument' to trigger cross-origin handling
    }
    main_root = {
        "nodeId": 1,
        "backendNodeId": 101,
        "nodeType": 1,
        "nodeName": "HTML",
        "nodeValue": "",
        "attributes": [],
        "children": [iframe_node],
    }

    # The iframe target's DOM (what the recursive get_dom_tree should return)
    iframe_root = {
        "nodeId": 10,
        "backendNodeId": 1000,
        "nodeType": 1,
        "nodeName": "HTML",
        "nodeValue": "",
        "attributes": [],
        "children": [],
    }

    # Our _get_all_trees stub will return different trees depending on target_id
    async def fake_get_all_trees(self, target_id):
        if target_id == MAIN_TARGET:
            return SimpleNamespace(
                cdp_timing={},
                dom_tree={"root": main_root},
                ax_tree={"nodes": []},
                snapshot={},  # passed to build_snapshot_lookup
                device_pixel_ratio=1.0,
                js_click_listener_backend_ids=set(),
            )
        elif target_id == IFRAME_TARGET_ID:
            return SimpleNamespace(
                cdp_timing={},
                dom_tree={"root": iframe_root},
                ax_tree={"nodes": []},
                snapshot={},
                device_pixel_ratio=1.0,
                js_click_listener_backend_ids=set(),
            )
        else:
            raise RuntimeError("Unexpected target_id in fake_get_all_trees")

    monkeypatch.setattr(DomService, "_get_all_trees", fake_get_all_trees)

    # Build snapshot lookup such that the iframe backendNodeId has bounds >=50 so it is processed
    class Bounds:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    class ScrollRects:
        def __init__(self, x=0, y=0):
            self.x = x
            self.y = y

    def fake_build_snapshot_lookup(snapshot_obj, device_pixel_ratio):
        # Create snapshot entries for backendNodeId 200 (iframe) with bounds >=50 and clientRects
        return {
            200: SimpleNamespace(bounds=Bounds(10, 20, 200, 150), scrollRects=ScrollRects(0, 0), clientRects=SimpleNamespace(height=600), computed_styles={}),
            101: SimpleNamespace(bounds=Bounds(0, 0, 800, 600), scrollRects=ScrollRects(0, 0), computed_styles={}),
            1000: SimpleNamespace(bounds=Bounds(0, 0, 300, 200), scrollRects=ScrollRects(0, 0), computed_styles={}),
        }

    monkeypatch.setattr(service_module, "build_snapshot_lookup", fake_build_snapshot_lookup)

    # Prepare all_frames mapping returned by browser_session.get_all_frames for iframe matching
    all_frames_map = {
        # frame id that matches the src base (without query)
        "frame-1": {"url": "https://example.com/path", "frameTargetId": IFRAME_TARGET_ID, "title": "IframeTitle"},
    }

    # Prepare session_manager targets map so get_target returns an object with url/title/type
    target_map = {
        IFRAME_TARGET_ID: SimpleNamespace(url="https://example.com/path", title="IframeTitle", target_type="iframe")
    }

    fake_browser_session = FakeBrowserSession(target_map, all_frames_map)

    # Ensure is_element_visible_according_to_all_parents returns True (so iframe is considered visible)
    monkeypatch.setattr(
        DomService,
        "is_element_visible_according_to_all_parents",
        classmethod(lambda cls, node, html_frames, viewport_threshold: True),
    )

    dom_service = DomService(fake_browser_session, logger=logger, cross_origin_iframes=True)

    enhanced_node, timing_info = await dom_service.get_dom_tree(MAIN_TARGET)

    # Assertions: main root should contain one child (iframe), whose content_document should be populated
    assert enhanced_node is not None
    # Find iframe child
    iframe_children = [c for c in (enhanced_node.children_nodes or []) if c.tag_name and c.tag_name.upper() == "IFRAME"]
    assert len(iframe_children) == 1
    iframe_enhanced = iframe_children[0]
    # Because we configured frameTargetId and the session manager, content_document should be filled by recursive call
    assert iframe_enhanced.content_document is not None
    # And the content_document parent should be the iframe node
    assert iframe_enhanced.content_document.parent_node is iframe_enhanced
    # The recursive iframe content root node id matches what fake_get_all_trees returned for iframe target
    assert iframe_enhanced.content_document.node_id == iframe_root["nodeId"]
    # Timing info contains expected keys
    assert "get_all_trees_total_ms" in timing_info
    assert "construct_enhanced_tree_ms" in timing_info
