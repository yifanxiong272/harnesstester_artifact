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
        """Ensure parser skips tokens that don't start with '--' and continues parsing."""
        # First token does not start with '--' and should be skipped by the parser.
        args = ["positional_token", "--foo.bar", "123", "--baz=hello"]
        result = _parse_args_to_nested_dict(args)

        # The parser should have ignored the positional token and parsed the remaining flags.
        self.assertEqual(result["foo"]["bar"], 123)
        self.assertEqual(result["baz"], "hello")
