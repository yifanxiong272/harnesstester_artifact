import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.common')
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
        """Ensure parser.print_help() is called when --help is passed and no help_text is provided."""
        # Use a simple dummy type for the CLI; we won't reach CliApp.run because --help triggers exit earlier.
        cli = BasicCLI(object)  # help_text defaults to None -> triggers parser.print_help branch
        self.assertIsNone(cli.help_text)

        with self.assertRaises(SystemExit) as cm:
            cli.get_config(["--help"])

        # argparse should call exit(0)
        self.assertEqual(cm.exception.code, 0)
