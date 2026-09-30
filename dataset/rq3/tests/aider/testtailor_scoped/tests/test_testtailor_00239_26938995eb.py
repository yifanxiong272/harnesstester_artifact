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
        """Ensure basic_lint handles a RecursionError from traverse_tree by printing and returning."""
        # Prepare a fake parser whose parse returns a tree with a root_node (value not used
        # because traverse_tree will be patched to raise).
        parser_mock = MagicMock()
        fake_tree = MagicMock()
        fake_tree.root_node = MagicMock()
        parser_mock.parse.return_value = fake_tree

        fname = "file.py"
        code = "def foo(): pass"

        # Patch filename_to_lang to return a supported language and get_parser to return our parser.
        # Patch traverse_tree in the module where basic_lint is defined to raise RecursionError.
        module_path = basic_lint.__module__
        with patch(f"{module_path}.filename_to_lang", return_value="python"), patch(
            f"{module_path}.get_parser", return_value=parser_mock
        ), patch(f"{module_path}.traverse_tree", side_effect=RecursionError), patch(
            "builtins.print"
        ) as mock_print:
            result = basic_lint(fname, code)

            # basic_lint should have printed the RecursionError message and returned None
            mock_print.assert_called_once_with(f"Unable to lint {fname} due to RecursionError")
            self.assertIsNone(result)
