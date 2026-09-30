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
        """Ensure a trailing flag without a value causes the parser to break out
        and return an empty result (no partial key created)."""
        args = ["--orphan_flag"]  # flag with no '=' and no following value
        result = _parse_args_to_nested_dict(args)
        # The parser should break before creating any key/value pairs.
        self.assertEqual(len(result), 0)
