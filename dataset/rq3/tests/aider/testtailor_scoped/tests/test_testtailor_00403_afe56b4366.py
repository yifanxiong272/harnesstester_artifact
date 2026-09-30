import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.linter')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure traverse_tree iterates over node.children and collects errors recursively."""
        # simple Node class to mimic the structure expected by traverse_tree
        class Node:
            def __init__(self, type_, is_missing, start_point, children=None):
                self.type = type_
                self.is_missing = is_missing
                self.start_point = start_point
                self.children = children or []

        # Create a tree:
        # root
        # ├─ child1 (ERROR) -> line 10
        # └─ child2 (is_missing=True) -> line 20
        #     └─ child3 (ERROR) -> line 30
        child1 = Node("ERROR", False, (10, 0))
        child3 = Node("ERROR", False, (30, 0))
        child2 = Node("OK", True, (20, 0), children=[child3])
        root = Node("ROOT", False, (0, 0), children=[child1, child2])

        errors = traverse_tree(root)

        # Expect DFS pre-order accumulation: child1, child2, child3
        self.assertEqual(errors, [10, 20, 30])
