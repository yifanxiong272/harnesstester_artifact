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
        """basic_lint should return None when traverse_tree finds no errors."""
        # Determine the module where basic_lint is defined so we patch the correct names.
        module = basic_lint.__module__

        # Patch the helper functions used by basic_lint within its module.
        with patch(f"{module}.filename_to_lang", return_value="python") as mock_fname, \
             patch(f"{module}.get_parser") as mock_get_parser, \
             patch(f"{module}.traverse_tree", return_value=[]) as mock_traverse:

            # Mock parser and parse result (tree with a root_node)
            mock_parser = MagicMock()
            mock_tree = MagicMock()
            mock_parser.parse.return_value = mock_tree
            mock_get_parser.return_value = mock_parser

            # Call the function under test
            result = basic_lint("test.py", "print('hello')")

            # When no errors are found, basic_lint should return None
            self.assertIsNone(result)

            # Ensure parser was requested for the returned language and traverse_tree was used
            mock_get_parser.assert_called_once_with("python")
            mock_traverse.assert_called_once_with(mock_tree.root_node)
