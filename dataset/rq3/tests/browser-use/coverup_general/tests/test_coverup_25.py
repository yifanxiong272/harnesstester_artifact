# file: browser_use/dom/serializer/serializer.py:617-727
# asked: {"lines": [619, 620, 623, 625, 626, 627, 630, 631, 633, 634, 635, 636, 638, 639, 640, 642, 643, 644, 647, 648, 649, 654, 655, 656, 657, 658, 664, 665, 666, 667, 668, 669, 674, 675, 677, 678, 679, 680, 681, 684, 685, 687, 688, 689, 690, 691, 693, 695, 697, 700, 702, 703, 704, 706, 709, 711, 713, 714, 717, 718, 719, 721, 722, 723, 726, 727], "branches": [[619, 620], [619, 623], [623, 625], [623, 726], [630, 631], [630, 654], [637, 642], [637, 647], [675, 677], [675, 704], [695, 697], [695, 700], [702, 703], [702, 709], [704, 706], [704, 709], [709, 711], [709, 726], [717, 718], [717, 719], [719, 721], [719, 726], [722, 723], [722, 726], [726, 0], [726, 727]]}
# gained: {"lines": [619, 620, 623, 625, 626, 627, 630, 631, 633, 634, 635, 636, 638, 639, 640, 642, 643, 644, 654, 655, 656, 657, 658, 664, 665, 666, 667, 668, 669, 674, 675, 677, 678, 679, 680, 681, 684, 685, 687, 688, 689, 690, 691, 693, 695, 697, 700, 702, 704, 706, 709, 711, 713, 714, 717, 718, 719, 721, 722, 723, 726, 727], "branches": [[619, 620], [619, 623], [623, 625], [623, 726], [630, 631], [630, 654], [637, 642], [675, 677], [675, 704], [695, 697], [695, 700], [702, 709], [704, 706], [709, 711], [709, 726], [717, 718], [717, 719], [719, 721], [722, 723], [726, 0], [726, 727]]}

import types
import pytest

from browser_use.dom.serializer.serializer import DOMTreeSerializer
from browser_use.dom.views import SimplifiedNode

def make_original_node(
    backend_node_id: int,
    *,
    snapshot_node=True,
    is_visible=False,
    is_actually_scrollable=False,
    attributes=None,
    tag_name=None,
):
    if attributes is None:
        attributes = {}
    return types.SimpleNamespace(
        backend_node_id=backend_node_id,
        snapshot_node=snapshot_node,
        is_visible=is_visible,
        is_actually_scrollable=is_actually_scrollable,
        attributes=attributes,
        tag_name=tag_name,
    )

def test_assign_none_returns_no_change():
    # Create a minimal serializer with a dummy root (not used)
    root = types.SimpleNamespace()
    ser = DOMTreeSerializer(root)
    original_counter = ser._interactive_counter
    # Call with None - should return early and not change counter or selector map
    ser._assign_interactive_indices_and_mark_new_nodes(None)
    assert ser._interactive_counter == original_counter
    assert ser._selector_map == {}

def test_file_input_shadow_and_compound_component_marks_interactive_and_new():
    # Prepare a serializer
    root = types.SimpleNamespace()
    ser = DOMTreeSerializer(root)

    # Create an original node that is interactive (cached), has no snapshot_node and is an input file in shadow DOM
    orig = make_original_node(
        101,
        snapshot_node=False,
        is_visible=False,
        is_actually_scrollable=False,
        attributes={'type': 'file', 'name': 'upl', 'id': 'f1'},
        tag_name='INPUT',
    )
    node = SimplifiedNode(original_node=orig, children=[], is_compound_component=True)

    # Force interactivity cached and inside shadow DOM
    ser._is_interactive_cached = lambda n: True
    ser._is_inside_shadow_dom = lambda n: True
    # previous map present but should not be used because is_compound_component True
    ser._previous_cached_selector_map = {'x': types.SimpleNamespace(backend_node_id=999)}

    # Run assignment
    ser._assign_interactive_indices_and_mark_new_nodes(node)

    # Assertions: interactive, added to selector_map, counter incremented, and marked new due to compound
    assert node.is_interactive is True
    assert node.is_new is True
    assert 101 in ser._selector_map
    assert ser._selector_map[101] is orig
    assert ser._interactive_counter == 2  # started at 1, incremented once

def test_scrollable_dropdown_and_excluded_parent_child_processing():
    root = types.SimpleNamespace()
    ser = DOMTreeSerializer(root)

    # Configure cached interactivity; we'll have mixed behavior via _has_interactive_descendants
    ser._is_interactive_cached = lambda n: True
    # For this test, not in shadow DOM
    ser._is_inside_shadow_dom = lambda n: False

    # Case A: Dropdown container by class -> should be indexed regardless of descendants
    orig_dropdown = make_original_node(
        201,
        snapshot_node=True,
        is_visible=True,
        is_actually_scrollable=True,
        attributes={'class': 'foo dropdown-menu bar', 'role': ''},
        tag_name='div',
    )
    node_dropdown = SimplifiedNode(original_node=orig_dropdown, children=[], is_compound_component=False)

    # Ensure _has_interactive_descendants won't be called for dropdown container path, but define it anyway
    ser._has_interactive_descendants = lambda n: True  # would normally prevent indexing if not a dropdown

    # previous cached selector map that does NOT contain 201 so is_new should be True
    ser._previous_cached_selector_map = {'a': types.SimpleNamespace(backend_node_id=999)}

    ser._assign_interactive_indices_and_mark_new_nodes(node_dropdown)

    assert node_dropdown.is_interactive is True
    assert node_dropdown.is_new is True
    assert 201 in ser._selector_map
    assert ser._selector_map[201] is orig_dropdown

    # Case B: Scrollable non-dropdown with interactive descendants -> should NOT become interactive
    orig_scrollable = make_original_node(
        202,
        snapshot_node=True,
        is_visible=True,
        is_actually_scrollable=True,
        attributes={'class': 'scrollable', 'role': ''},
        tag_name='div',
    )
    # Create a child that is interactive (simulate interactive descendant)
    orig_child = make_original_node(
        203,
        snapshot_node=True,
        is_visible=True,
        is_actually_scrollable=False,
        attributes={'type': 'button'},
        tag_name='button',
    )
    child_node = SimplifiedNode(original_node=orig_child, children=[], is_compound_component=False)
    parent_node = SimplifiedNode(original_node=orig_scrollable, children=[child_node], is_compound_component=False)

    # Now define _has_interactive_descendants to return True for this parent
    def has_desc(n):
        # Return True if node has children (simulate interactive descendant presence)
        return bool(n.children)
    ser._has_interactive_descendants = has_desc

    # Reset previous selector map so child absence/newness logic is exercised
    ser._previous_cached_selector_map = {'z': types.SimpleNamespace(backend_node_id=9999)}

    # Run assignment on parent which should process child and make the child interactive but not the parent
    ser._assign_interactive_indices_and_mark_new_nodes(parent_node)

    # Parent should not be interactive because it has interactive descendants
    assert parent_node.is_interactive is False
    # Child should be interactive and added to selector map
    assert child_node.is_interactive is True
    assert 203 in ser._selector_map
    assert ser._selector_map[203] is orig_child

    # Also verify that recursion processes children of excluded parents:
    # Make an excluded parent with an interactive child; parent should not be indexed but child should.
    excluded_parent_orig = make_original_node(
        301,
        snapshot_node=True,
        is_visible=True,
        is_actually_scrollable=False,
        attributes={},
        tag_name='div',
    )
    excluded_child_orig = make_original_node(
        302,
        snapshot_node=True,
        is_visible=True,
        is_actually_scrollable=False,
        attributes={'type': 'button'},
        tag_name='button',
    )
    excluded_child = SimplifiedNode(original_node=excluded_child_orig, children=[], is_compound_component=False)
    excluded_parent = SimplifiedNode(original_node=excluded_parent_orig, children=[excluded_child], excluded_by_parent=True)

    # Ensure interactivity cached returns True for child
    ser._is_interactive_cached = lambda n: True

    ser._assign_interactive_indices_and_mark_new_nodes(excluded_parent)

    # Parent should remain non-interactive because excluded_by_parent True
    assert excluded_parent.is_interactive is False
    # Child should be processed and interactive
    assert excluded_child.is_interactive is True
    assert 302 in ser._selector_map
    assert ser._selector_map[302] is excluded_child_orig
