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
        """Creating a Command with a signature that omits an argument placeholder should raise ValueError."""
        # Prepare arguments: one present in the signature, one missing
        args = [
            Argument(name="present", type="string", description="an arg that is present", required=True),
            Argument(name="missing", type="string", description="an arg that is missing", required=True),
        ]

        # Signature only includes the 'present' argument placeholder, so 'missing' is omitted
        signature = "mycmd <present>"

        with self.assertRaises(ValueError) as cm:
            Command(
                name="mycmd",
                docstring="A command whose signature is missing an argument placeholder",
                signature=signature,
                arguments=args,
            )

        msg = str(cm.exception)
        self.assertIn("Missing arguments in signature", msg)
        self.assertIn("Did you format the signature correctly", msg)
        self.assertIn("You must include all argument names", msg)
        # ensure the signature itself is referenced in the message
        self.assertIn(signature, msg)
