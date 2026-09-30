import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.args_formatter')
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
        """Ensure when action.default is argparse.SUPPRESS the formatter emits an empty default value."""
        fmt = DotEnvFormatter("prog")
        # create a simple action-like object with the attributes used by _format_action
        action = type("Action", (), {})()
        action.option_strings = ["--foo"]
        action.env_var = "FOO"
        action.default = argparse.SUPPRESS
        action.help = "some help"

        result = fmt._format_action(action)
        expected = "\n## some help\n#FOO=\n\n"
        self.assertEqual(result, expected)
