import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.quick_stats')
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
        """Verify get_cli_parser defines a positional optional 'directory' argument with Path type and correct defaults/help."""
        parser = get_cli_parser()

        # Find the 'directory' action
        dir_actions = [a for a in parser._actions if a.dest == "directory"]
        self.assertTrue(dir_actions, "Parser does not define a 'directory' argument")
        action = dir_actions[0]

        # Check configured properties on the action
        self.assertEqual(action.nargs, "?")
        self.assertIs(action.type, Path)
        self.assertEqual(action.default, Path("."))
        self.assertIn("Directory to search for .traj files", action.help)

        # Check parse_args behavior with no arguments (should use default Path('.'))
        ns_default = parser.parse_args([])
        self.assertIsInstance(ns_default.directory, Path)
        self.assertEqual(ns_default.directory, Path("."))

        # Check parse_args behavior with a provided directory string (should convert to Path)
        ns_given = parser.parse_args(["/tmp/some_dir"])
        self.assertIsInstance(ns_given.directory, Path)
        self.assertEqual(ns_given.directory, Path("/tmp/some_dir"))
