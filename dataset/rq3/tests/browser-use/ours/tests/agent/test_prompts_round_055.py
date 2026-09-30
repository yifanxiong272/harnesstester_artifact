import builtins
from types import SimpleNamespace
from browser_use.agent.prompts import AgentMessagePrompt
from browser_use.dom.views import NodeType


def make_original(node_type, tag_name=None, is_actually_scrollable=False, node_value=None, shadow_root_type=None):
    """Create a lightweight stand-in for the original_node expected by the traversal."""
    return SimpleNamespace(
        node_type=node_type,
        tag_name=tag_name,
        is_actually_scrollable=is_actually_scrollable,
        node_value=node_value,
        shadow_root_type=shadow_root_type,
    )


def make_node(original_node, children=None, is_interactive=False, is_shadow_host=False):
    """Create a lightweight stand-in for the SimplifiedNode expected by the traversal."""
    return SimpleNamespace(
        original_node=original_node,
        children=children or [],
        is_interactive=is_interactive,
        is_shadow_host=is_shadow_host,
    )


def baseline_stats():
    return {
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


def test_extract_page_statistics_empty_dom_round_055():
    """When dom_state is missing or _root falsy, stats should equal the baseline."""
    # dom_state is None -> early return path
    browser_state = SimpleNamespace(dom_state=None)
    prompt = AgentMessagePrompt(browser_state, None)
    assert prompt._extract_page_statistics() == baseline_stats()

    # dom_state exists but _root is falsy -> early return
    browser_state = SimpleNamespace(dom_state=SimpleNamespace(_root=None))
    prompt = AgentMessagePrompt(browser_state, None)
    assert prompt._extract_page_statistics() == baseline_stats()


def test_extract_page_statistics_complex_tree_round_055():
    """Build a small DOM tree exercising element/text/iframe/img/shadow branches and children traversal."""
    # Text node child of anchor
    text_orig = make_original(NodeType.TEXT_NODE, node_value=' hello ')
    text_node = make_node(text_orig, children=[], is_interactive=False, is_shadow_host=False)

    # Anchor element (interactive) with text child
    anchor_orig = make_original(NodeType.ELEMENT_NODE, tag_name='A')
    anchor_node = make_node(anchor_orig, children=[text_node], is_interactive=True, is_shadow_host=False)

    # Iframe element
    iframe_orig = make_original(NodeType.ELEMENT_NODE, tag_name='iframe')
    iframe_node = make_node(iframe_orig)

    # Img element that is actually scrollable
    img_orig = make_original(NodeType.ELEMENT_NODE, tag_name='img', is_actually_scrollable=True)
    img_node = make_node(img_orig)

    # Shadow host with one closed and one open fragment child -> should count as shadow_closed
    docfrag_closed_orig = make_original(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='closed')
    docfrag_closed_node = make_node(docfrag_closed_orig)

    docfrag_open_orig = make_original(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='open')
    docfrag_open_node = make_node(docfrag_open_orig)

    host_closed_orig = make_original(NodeType.ELEMENT_NODE, tag_name='div')
    host_closed_node = make_node(host_closed_orig, children=[docfrag_closed_node, docfrag_open_node], is_shadow_host=True)

    # Shadow host with only open fragment -> should count as shadow_open
    docfrag_open2_orig = make_original(NodeType.DOCUMENT_FRAGMENT_NODE, shadow_root_type='open')
    docfrag_open2_node = make_node(docfrag_open2_orig)

    host_open_orig = make_original(NodeType.ELEMENT_NODE, tag_name='section')
    host_open_node = make_node(host_open_orig, children=[docfrag_open2_node], is_shadow_host=True)

    # A child with original_node falsy should be skipped (covers the early return inside traverse)
    missing_orig_node = make_node(None)

    # Root element with all children
    root_orig = make_original(NodeType.ELEMENT_NODE, tag_name='div')
    root_children = [anchor_node, missing_orig_node, iframe_node, img_node, host_closed_node, host_open_node]
    root_node = make_node(root_orig, children=root_children)

    browser_state = SimpleNamespace(dom_state=SimpleNamespace(_root=root_node))

    prompt = AgentMessagePrompt(browser_state, None)
    stats = prompt._extract_page_statistics()

    # Compute expected counts from the constructed tree:
    # Elements counted: root, anchor, text node, iframe, img, host_closed, docfrag_closed, docfrag_open, host_open, docfrag_open2 = 10
    expected = baseline_stats()
    expected.update({
        'total_elements': 10,
        'links': 1,  # anchor
        'iframes': 1,  # iframe
        'images': 1,  # img
        'scroll_containers': 1,  # img is actually scrollable
        'interactive_elements': 1,  # anchor
        'shadow_closed': 1,  # host_closed has a closed fragment
        'shadow_open': 1,  # host_open only has open fragment
        'text_chars': len('hello'),  # stripped from ' hello '
    })

    assert stats == expected, f"unexpected stats: {stats} vs expected {expected}"
