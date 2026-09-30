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
        """basic_lint should return None (early return) when there are no errors."""
        fname = "example.py"
        code = "print('hello')"

        # Get the module where basic_lint is defined so we can patch its internals
        module = sys.modules[basic_lint.__module__]

        # Patch filename_to_lang to return a valid non-typescript language,
        # get_parser to return a mock parser, and traverse_tree to return no errors.
        with patch.object(module, "filename_to_lang", return_value="python") as mock_ftl, \
             patch.object(module, "get_parser") as mock_get_parser, \
             patch.object(module, "traverse_tree", return_value=[]) as mock_traverse:

            # Prepare parser and tree mocks
            mock_parser = MagicMock()
            mock_tree = MagicMock()
            mock_parser.parse.return_value = mock_tree
            mock_get_parser.return_value = mock_parser

            # Call the function under test
            result = basic_lint(fname, code)

            # Expect early return (None) when no errors
            self.assertIsNone(result)

            # Verify interactions
            mock_ftl.assert_called_once_with(fname)
            mock_get_parser.assert_called_once_with("python")
            mock_parser.parse.assert_called_once_with(bytes(code, "utf-8"))
            mock_traverse.assert_called_once_with(mock_tree.root_node)
