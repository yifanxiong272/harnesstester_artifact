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
        """Ensure basic_lint calls parser.parse with bytes(code, 'utf-8') and returns LintResult
        when the tree contains an ERROR node."""
        fname = "example.py"
        code = "print('hello')\n"

        # Create fake parser/tree/node objects
        class FakeNode:
            def __init__(self):
                # Mark this node as an error so traverse_tree will collect it
                self.type = "ERROR"
                self.is_missing = False
                # start_point is (line_index, column) and traverse_tree uses index [0]
                self.start_point = (7, 0)
                self.children = []

        class FakeTree:
            def __init__(self):
                self.root_node = FakeNode()

        class FakeParser:
            def __init__(self):
                self.parse_called_with = None

            def parse(self, b):
                # record what was passed in and return a fake tree
                self.parse_called_with = b
                return FakeTree()

        fake_parser = FakeParser()

        # Patch the functions used by basic_lint in its global namespace:
        # - filename_to_lang should return a non-empty language (not 'typescript')
        # - get_parser should return our fake parser
        with patch.dict(
            basic_lint.__globals__,
            {
                "filename_to_lang": (lambda fname: "python"),
                "get_parser": (lambda lang: fake_parser),
            },
        ):
            result = basic_lint(fname, code)

        # basic_lint should have invoked parser.parse with bytes(code, 'utf-8')
        self.assertEqual(fake_parser.parse_called_with, bytes(code, "utf-8"))

        # Because the fake tree root node is an ERROR, basic_lint should return a LintResult
        self.assertIsInstance(result, LintResult)
        # text should be empty and lines should contain the line number from start_point
        self.assertEqual(result.text, "")
        self.assertEqual(result.lines, [7])
