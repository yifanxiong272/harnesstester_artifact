# file: browser_use/dom/enhanced_snapshot.py:46-181
# asked: {"lines": [51, 53, 54, 56, 57, 59, 60, 62, 63, 64, 67, 68, 69, 70, 73, 74, 75, 76, 81, 82, 83, 84, 85, 91, 92, 95, 96, 97, 98, 101, 102, 103, 104, 107, 108, 109, 110, 111, 112, 113, 115, 116, 119, 122, 123, 124, 125, 126, 130, 131, 132, 133, 136, 137, 140, 141, 142, 143, 144, 145, 146, 147, 148, 152, 153, 154, 155, 156, 157, 158, 159, 160, 164, 165, 167, 168, 169, 170, 171, 172, 173, 174, 175, 179, 180, 181], "branches": [[56, 57], [56, 59], [62, 63], [62, 179], [68, 69], [68, 73], [69, 70], [69, 73], [82, 83], [82, 91], [83, 84], [83, 91], [84, 83], [84, 85], [95, 62], [95, 96], [97, 98], [97, 101], [111, 112], [111, 167], [113, 115], [113, 167], [116, 119], [116, 130], [130, 131], [130, 136], [136, 137], [136, 140], [141, 142], [141, 152], [143, 144], [143, 152], [153, 154], [153, 164], [155, 156], [155, 164], [164, 165], [164, 167]]}
# gained: {"lines": [51, 53, 54, 56, 57, 59, 60, 62, 63, 64, 67, 68, 69, 70, 73, 74, 75, 76, 81, 82, 83, 84, 85, 91, 92, 95, 96, 97, 98, 101, 102, 103, 104, 107, 108, 109, 110, 111, 112, 113, 115, 116, 119, 122, 123, 124, 125, 126, 130, 131, 132, 133, 136, 137, 140, 141, 142, 143, 144, 145, 146, 147, 148, 152, 153, 154, 155, 156, 157, 158, 159, 160, 164, 165, 167, 168, 169, 170, 171, 172, 173, 174, 175, 179, 180, 181], "branches": [[56, 57], [56, 59], [62, 63], [62, 179], [68, 69], [68, 73], [69, 70], [69, 73], [82, 83], [83, 84], [83, 91], [84, 85], [95, 62], [95, 96], [97, 98], [111, 112], [113, 115], [116, 119], [116, 130], [130, 131], [136, 137], [141, 142], [143, 144], [143, 152], [153, 154], [155, 156], [155, 164], [164, 165], [164, 167]]}

import pytest

from browser_use.dom.enhanced_snapshot import build_snapshot_lookup


def test_empty_documents_returns_empty():
    snapshot = {"documents": [], "strings": []}
    result = build_snapshot_lookup(snapshot, device_pixel_ratio=1.0)
    assert isinstance(result, dict)
    assert result == {}


def test_no_backend_nodeid_results_in_empty_lookup():
    # Document present but nodes has no 'backendNodeId' key -> no entries in lookup
    snapshot = {
        "documents": [
            {
                "nodes": {},  # no backendNodeId
                "layout": {"nodeIndex": []},
                # documentURL intentionally out-of-range to hit 'N/A' branch for logging
                "documentURL": 999,
            }
        ],
        "strings": [],
    }
    result = build_snapshot_lookup(snapshot, device_pixel_ratio=1.0)
    assert isinstance(result, dict)
    assert result == {}


def test_build_snapshot_lookup_full_parsing():
    # Prepare strings so style indices map correctly into REQUIRED_COMPUTED_STYLES
    strings = [
        "http://example",  # 0 documentURL
        "display",         # 1
        "visibility",      # 2
        "opacity",         # 3
        "overflow",        # 4
        "overflow-x",      # 5
        "overflow-y",      # 6
        "cursor-style",    # 7 -> should map to 'cursor'
        "pointer-events",  # 8
        "position",        # 9
        "background",      # 10
    ]

    # Two backend nodes with snapshot indices 0 and 1
    nodes = {
        "backendNodeId": [111, 222],
        # Mark only the second snapshot index as clickable
        "isClickable": {"index": [1]},
    }

    # Layout maps snapshot index 0 -> layout idx 0 ; 1 -> layout idx 1
    layout = {
        "nodeIndex": [0, 1],
        # bounds: first has >=4 entries, second has fewer than 4 to avoid creating bounding box
        "bounds": [
            [10, 20, 30, 40],  # layout idx 0 -> will produce bounding box
            [1, 2, 3],         # layout idx 1 -> ignored (len < 4)
        ],
        # styles: first layout entry has indices mapping into `strings` list
        "styles": [
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            [],  # second entry has no styles
        ],
        "paintOrders": [5, 6],
        "clientRects": [
            [100, 110, 120, 130],
            None,
        ],
        "scrollRects": [
            [200, 210, 220, 230],
            [],  # insufficient, so ignored
        ],
        # stackingContexts is a dict; len(dict) == 1 so layout_idx 0 will be < 1 and accessed
        "stackingContexts": {"index": [777, 888]},
    }

    document = {"nodes": nodes, "layout": layout, "documentURL": 0}
    snapshot = {"documents": [document], "strings": strings}

    # Use device_pixel_ratio 2.0 to ensure DOMRect values are divided
    lookup = build_snapshot_lookup(snapshot, device_pixel_ratio=2.0)

    # Both backend node ids should be present
    assert set(lookup.keys()) == {111, 222}

    node_111 = lookup[111]
    node_222 = lookup[222]

    # Node 111 corresponds to snapshot index 0 and should have bounding box scaled by 2.0
    assert node_111.bounds is not None
    assert pytest.approx(node_111.bounds.x) == 10 / 2.0
    assert pytest.approx(node_111.bounds.y) == 20 / 2.0
    assert pytest.approx(node_111.bounds.width) == 30 / 2.0
    assert pytest.approx(node_111.bounds.height) == 40 / 2.0

    # clientRects and scrollRects should be present for node_111
    assert node_111.clientRects is not None
    assert node_111.clientRects.x == 100
    assert node_111.clientRects.y == 110
    assert node_111.clientRects.width == 120
    assert node_111.clientRects.height == 130

    assert node_111.scrollRects is not None
    assert node_111.scrollRects.x == 200
    assert node_111.scrollRects.y == 210
    assert node_111.scrollRects.width == 220
    assert node_111.scrollRects.height == 230

    # computed_styles should be a dict and contain the 'cursor' mapping from strings[7]
    assert isinstance(node_111.computed_styles, dict)
    assert node_111.cursor_style == "cursor-style"
    # paint order and stacking contexts extracted
    assert node_111.paint_order == 5
    assert node_111.stacking_contexts == 777

    # Node 222 corresponds to snapshot index 1 and should NOT have bounds (len(bounds) < 4)
    assert node_222.bounds is None
    # computed_styles for node_222 should be None (empty styles list yields None)
    assert node_222.computed_styles is None
    # Node 222 should be clickable due to isClickable.index containing 1
    assert node_222.is_clickable is True
    # Node 111 was not marked clickable
    assert node_111.is_clickable is False
