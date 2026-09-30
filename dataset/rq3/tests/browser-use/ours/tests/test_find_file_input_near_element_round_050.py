import pytest

from browser_use.browser import session as session_mod

# Grab the unbound method to call with a fake self
_find_fn = session_mod.BrowserSession.find_file_input_near_element


class FakeNode:
    """Lightweight stand-in for EnhancedDOMTreeNode used by the method under test."""

    def __init__(self, name, is_input=False, children=None, parent=None):
        self.name = name
        # attribute checked by our FakeSelf.is_file_input
        self.is_input = is_input
        # API used by the function under test
        self.children_nodes = children or []
        self.parent_node = parent
        # ensure children know their parent when constructed with children list
        for c in self.children_nodes:
            c.parent_node = self

    def __repr__(self):
        return f"<FakeNode {self.name}>"


class FakeSelf:
    """Provides the is_file_input contract expected by the real BrowserSession instance.

    The real method signature is (self, element). We mirror that here so the
    unbound function can be invoked as if on a BrowserSession instance.
    """

    def is_file_input(self, element):
        # Deterministic: rely only on element.is_input boolean
        return bool(getattr(element, "is_input", False))


def test_node_is_file_input_round_050():
    """If the starting node itself is a file input, it should be returned."""
    node = FakeNode("n1", is_input=True)
    fake_self = FakeSelf()

    result = _find_fn(fake_self, node, max_height=3, max_descendant_depth=3)

    assert result is node, "Should return the node itself when it is a file input"


def test_descendant_found_round_050():
    """A descendant within max_descendant_depth should be discovered and returned."""
    child = FakeNode("child", is_input=True)
    root = FakeNode("root", is_input=False, children=[child])
    fake_self = FakeSelf()

    # allow 1 level of descendant search
    result = _find_fn(fake_self, root, max_height=0, max_descendant_depth=1)

    assert result is child, "Should return the descendant that is a file input"


def test_sibling_descendant_and_parent_traversal_round_050():
    """If the current node and its descendants don't match, siblings and their
    descendants should be searched, and the algorithm should traverse up parents.

    This builds a tree where the desired file input is in a sibling's descendant.
    """
    # target sits two levels under the parent of current
    target = FakeNode("target", is_input=True)
    s_child = FakeNode("s_child", is_input=False, children=[target])
    sibling = FakeNode("sibling", is_input=False, children=[s_child])

    current = FakeNode("current", is_input=False)
    parent = FakeNode("parent", is_input=False, children=[current, sibling])
    # ensure parent's children have parent_node set (FakeNode constructor does this)

    fake_self = FakeSelf()

    # allow traversing up one parent and searching descendants up to depth 2
    result = _find_fn(fake_self, current, max_height=1, max_descendant_depth=2)

    assert result is target, "Should find file input in a sibling's descendant"


def test_max_descendant_depth_negative_round_050():
    """When max_descendant_depth is negative, descendant search immediately returns None
    (exercises the depth < 0 early exit), and overall result should be None if
    no other matching nodes are present.
    """
    child = FakeNode("child", is_input=True)
    root = FakeNode("root", is_input=False, children=[child])
    fake_self = FakeSelf()

    # Negative descendant depth means _find_in_descendants returns None immediately
    res = _find_fn(fake_self, root, max_height=0, max_descendant_depth=-1)

    assert res is None, "With negative descendant depth and no matching siblings/parents, result is None"
