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
        """Passing --help_option should print help for the requested type and exit with code 0."""
        # Import here so the test function is self-contained (top-level imports not allowed per instructions)
        from sweagent.run.run_single import RunSingleConfig
        from sweagent.run.common import BasicCLI

        cli = BasicCLI(RunSingleConfig)
        args = ["--help_option", "sweagent.run.run_single.RunSingleConfig"]
        with self.assertRaises(SystemExit) as cm:
            cli.get_config(args)
        self.assertEqual(cm.exception.code, 0)
