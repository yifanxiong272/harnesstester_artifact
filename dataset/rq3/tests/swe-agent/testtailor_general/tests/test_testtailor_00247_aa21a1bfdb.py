import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.commands')
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
        """Creating a Command whose signature contains an extra placeholder
        not present in the arguments should raise a validation error about
        mismatched argument names.
        """
        # signature contains an extra placeholder "<xx>" that is not defined in arguments
        signature = "do <aa> [<bb>] <xx>"

        args = [
            Argument(name="aa", description="arg aa", type="string", required=True),
            Argument(name="bb", description="arg bb", type="string", required=False),
        ]

        # Pydantic wraps the ValueError raised in the model_validator into a ValidationError,
        # so catch a generic Exception and inspect the message.
        with self.assertRaises(Exception) as ctx:
            # construction triggers model validation (validate_arguments)
            Command(name="do", docstring="doc", signature=signature, arguments=args)

        msg = str(ctx.exception)
        # should mention the mismatch and include the extra placeholder name
        self.assertIn("do not match argument names", msg)
        self.assertIn("xx", msg)
