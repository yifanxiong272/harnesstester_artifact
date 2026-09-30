import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.config.arg_utils')
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
        """Verify get_subparser returns the specific subparser when it exists."""
        parser = ArgumentParser(prog="root")
        subparsers = parser.add_subparsers(dest="command")
        sp_alpha = subparsers.add_parser("alpha")
        sp_beta = subparsers.add_parser("beta")

        # This should follow the path where a _SubParsersAction is found
        # and the requested name exists in action.choices, hitting the return.
        result = get_subparser(parser, "beta")

        # The returned object should be the same ArgumentParser instance added for "beta"
        self.assertIs(result, sp_beta)
        self.assertIsInstance(result, ArgumentParser)
