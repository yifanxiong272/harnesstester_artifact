# file: aider/linter.py:260-269
# asked: {"lines": [261, 262, 263, 264, 266, 267, 269], "branches": [[262, 263], [262, 266], [266, 267], [266, 269]]}
# gained: {"lines": [261, 262, 263, 264, 266, 267, 269], "branches": [[262, 263], [262, 266], [266, 267], [266, 269]]}

import pytest
from dataclasses import dataclass
from typing import List, Tuple

from aider.linter import traverse_tree


@dataclass
class FakeNode:
    type: str
    is_missing: bool
    start_point: Tuple[int, int]
    children: List["FakeNode"]

    def __init__(self, type="NORMAL", is_missing=False, start_point=(0, 0), children=None):
        self.type = type
        self.is_missing = is_missing
        self.start_point = start_point
        self.children = children if children is not None else []


def test_traverse_tree_single_error_node():
    # Node whose type is 'ERROR' should produce its start_point[0] in the result
    node = FakeNode(type="ERROR", is_missing=False, start_point=(5, 10), children=[])
    result = traverse_tree(node)
    assert isinstance(result, list)
    assert result == [5]


def test_traverse_tree_single_missing_node():
    # Node that is missing should produce its start_point[0] in the result
    node = FakeNode(type="NORMAL", is_missing=True, start_point=(3, 0), children=[])
    result = traverse_tree(node)
    assert result == [3]


def test_traverse_tree_recursive_mixed_nodes():
    # Mixed tree: root is normal, children include error and missing nodes,
    # and one child has its own child that is missing to test recursion.
    child_error = FakeNode(type="ERROR", is_missing=False, start_point=(1, 0), children=[])
    child_missing = FakeNode(type="NORMAL", is_missing=True, start_point=(2, 0), children=[])
    grandchild_missing = FakeNode(type="NORMAL", is_missing=True, start_point=(4, 0), children=[])
    child_with_grandchild = FakeNode(type="NORMAL", is_missing=False, start_point=(7, 0), children=[grandchild_missing])

    root = FakeNode(type="NORMAL", is_missing=False, start_point=(0, 0),
                    children=[child_error, child_missing, child_with_grandchild])

    result = traverse_tree(root)
    # The order should follow the traversal: child_error, child_missing, then grandchild_missing
    assert result == [1, 2, 4]
