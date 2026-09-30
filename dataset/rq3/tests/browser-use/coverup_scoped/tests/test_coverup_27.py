# file: browser_use/agent/prompts.py:150-221
# asked: {"lines": [167, 169, 170, 172, 173, 176, 177, 179, 180, 181, 182, 183, 184, 187, 188, 191, 192, 195, 197, 198, 199, 200, 201, 203, 204, 206, 208, 209, 211, 214, 217, 218, 220, 221], "branches": [[164, 167], [169, 170], [169, 172], [176, 177], [176, 208], [179, 180], [179, 181], [181, 182], [181, 183], [183, 184], [183, 187], [187, 188], [187, 191], [191, 192], [191, 195], [195, 197], [195, 217], [203, 204], [203, 206], [208, 209], [208, 211], [211, 214], [211, 217], [217, 0], [217, 218]]}
# gained: {"lines": [167, 169, 170, 172, 173, 176, 177, 179, 180, 181, 182, 183, 184, 187, 188, 191, 192, 195, 197, 198, 199, 200, 201, 203, 204, 206, 208, 209, 211, 214, 217, 218, 220, 221], "branches": [[164, 167], [169, 170], [169, 172], [176, 177], [176, 208], [179, 180], [179, 181], [181, 182], [181, 183], [183, 184], [183, 187], [187, 188], [187, 191], [191, 192], [191, 195], [195, 197], [195, 217], [203, 204], [203, 206], [208, 209], [208, 211], [211, 214], [217, 0], [217, 218]]}

import pytest
from browser_use.agent.prompts import AgentMessagePrompt
from browser_use.dom.views import NodeType, SimplifiedNode


class FakeOriginal:
    def __init__(self, node_type, tag_name=None, is_actually_scrollable=False, node_value='', shadow_root_type=None):
        self.node_type = node_type
        self.tag_name = tag_name
        self.is_actually_scrollable = is_actually_scrollable
        self.node_value = node_value
        self.shadow_root_type = shadow_root_type


class FakeDOMState:
    def __init__(self, root):
        self._root = root


class FakeBrowserStateSummary:
    def __init__(self, dom_state):
        self.dom_state = dom_state


def test_extract_page_statistics_empty_dom():
    """If dom_state is missing or has no root, the default stats dict is returned."""
    fake_browser_state = FakeBrowserStateSummary(dom_state=None)
    amp = AgentMessagePrompt(browser_state_summary=fake_browser_state, file_system=None)
    stats = amp._extract_page_statistics()
    expected = {
        'links': 0,
        'iframes': 0,
        'shadow_open': 0,
        'shadow_closed': 0,
        'scroll_containers': 0,
        'images': 0,
        'interactive_elements': 0,
        'total_elements': 0,
        'text_chars': 0,
    }
    assert stats == expected


def test_extract_page_statistics_various_nodes():
    """
    Build a DOM with:
      - a root host with a closed shadow fragment child (counts as shadow_closed)
      - a separate host with an open shadow fragment child (counts as shadow_open)
      - an <a> interactive link with text child (counts link, interactive, and text_chars)
      - an <img> (counts image)
      - an <iframe> (counts iframe)
      - a scrollable <div> (counts scroll_containers)
      - a child node with original_node == None (should be skipped)
    Validate totals and per-type counters.
    """
    # Text node with whitespace to be trimmed to 'Hello' (5 chars)
    text_orig = FakeOriginal(NodeType.TEXT_NODE, node_value="  Hello  ")
    text_node = SimplifiedNode(original_node=text_orig, children=[])

    # Link node (interactive)
    link_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='A', is_actually_scrollable=False)
    link_node = SimplifiedNode(original_node=link_orig, children=[text_node], is_interactive=True)

    # Closed shadow fragment child
    fragment_closed_orig = FakeOriginal(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='closed')
    fragment_closed = SimplifiedNode(original_node=fragment_closed_orig, children=[])

    # Open shadow fragment child
    fragment_open_orig = FakeOriginal(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='OPEN')
    fragment_open = SimplifiedNode(original_node=fragment_open_orig, children=[])

    # Host with closed shadow (will be counted as shadow_closed)
    host_closed_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='div')
    host_closed = SimplifiedNode(original_node=host_closed_orig, children=[fragment_closed], is_shadow_host=True)

    # Host with open shadow (will be counted as shadow_open)
    host_open_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='section')
    host_open = SimplifiedNode(original_node=host_open_orig, children=[fragment_open], is_shadow_host=True)

    # Image node
    img_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='img')
    img_node = SimplifiedNode(original_node=img_orig, children=[])

    # Iframe node
    iframe_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='iframe')
    iframe_node = SimplifiedNode(original_node=iframe_orig, children=[])

    # Scrollable div
    scroll_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='div', is_actually_scrollable=True)
    scroll_node = SimplifiedNode(original_node=scroll_orig, children=[])

    # A node with no original_node should be skipped entirely
    skipped_node = SimplifiedNode(original_node=None, children=[])

    # Assemble root with all children
    root_children = [host_closed, link_node, img_node, iframe_node, scroll_node, host_open, skipped_node]
    root_orig = FakeOriginal(NodeType.ELEMENT_NODE, tag_name='body')
    root = SimplifiedNode(original_node=root_orig, children=root_children)

    fake_dom = FakeDOMState(root)
    fake_browser_state = FakeBrowserStateSummary(dom_state=fake_dom)
    amp = AgentMessagePrompt(browser_state_summary=fake_browser_state, file_system=None)

    stats = amp._extract_page_statistics()

    # Expected counts:
    # total_elements: root, host_closed, fragment_closed, link_node, text_node, img_node, iframe_node, scroll_node, host_open, fragment_open
    # skipped_node has original_node None -> not counted
    assert stats['total_elements'] == 10

    # link node should be counted
    assert stats['links'] == 1

    # iframe counted
    assert stats['iframes'] == 1

    # image counted
    assert stats['images'] == 1

    # scrollable counted
    assert stats['scroll_containers'] == 1

    # interactive elements counted (link_node)
    assert stats['interactive_elements'] == 1

    # shadow counts: one closed, one open
    assert stats['shadow_closed'] == 1
    assert stats['shadow_open'] == 1

    # text chars: 'Hello' -> length 5
    assert stats['text_chars'] == 5
