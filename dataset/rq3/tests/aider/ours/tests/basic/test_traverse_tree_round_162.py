from aider.linter import traverse_tree


class FakeNode:
    """Minimal node mimic for traverse_tree tests.

    Attributes match what traverse_tree expects: type, is_missing,
    start_point (indexable), and children (iterable).
    """

    def __init__(self, type, is_missing, start_point, children=None):
        self.type = type
        self.is_missing = is_missing
        self.start_point = start_point
        self.children = children or []


def test_traverse_tree_error_with_child_round_162():
    # Root is an ERROR and has one child that is also an ERROR.
    child = FakeNode("ERROR", False, (5,), [])
    root = FakeNode("ERROR", False, (1,), [child])

    # Expect root's line then child's line (depth-first aggregation).
    assert traverse_tree(root) == [1, 5]


def test_traverse_tree_non_error_children_round_162():
    # Root is normal, first child is missing (should contribute), second child normal.
    child_missing = FakeNode("X", True, (42,), [])
    child_normal = FakeNode("OK", False, (99,), [])
    root = FakeNode("OK", False, (0,), [child_missing, child_normal])

    # Only the missing child contributes its start_point[0].
    assert traverse_tree(root) == [42]


def test_traverse_tree_no_error_no_children_round_162():
    # Root is neither ERROR nor missing and has no children -> empty list.
    root = FakeNode("OK", False, (7,), [])
    assert traverse_tree(root) == []


def test_traverse_tree_missing_root_with_child_round_162():
    # Root is missing and has a child that is ERROR.
    child = FakeNode("ERROR", False, (2,), [])
    root = FakeNode("X", True, (100,), [child])

    # Root contributes its start_point then child's line is appended.
    assert traverse_tree(root) == [100, 2]
