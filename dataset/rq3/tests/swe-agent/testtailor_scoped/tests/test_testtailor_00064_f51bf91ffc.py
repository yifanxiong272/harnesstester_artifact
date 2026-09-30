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
        """Ensure that non-flag args are skipped (hits the i += 1; continue branch)
        and subsequent flags are still parsed correctly.
        """
        args = ["positional_arg", "--alpha.beta", "42"]
        result = _parse_args_to_nested_dict(args)

        # The initial positional element should be ignored, and the nested flag parsed.
        self.assertEqual(result["alpha"]["beta"], 42)
        # Ensure the positional argument did not become a key in the result
        self.assertNotIn("positional_arg", result)
