import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.utils')
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
        """Exercise get_signature when cmd.end_name is not None and a non-required argument appears
        before a dict-style final argument (to hit the branch that appends ' [<{param}>]').
        """
        class DummyArg:
            def __init__(self, name, required):
                self.name = name
                self.required = required

        class Cmd:
            pass

        cmd = Cmd()
        cmd.name = "mycmd"
        # First element: object with .name and .required (non-required -> triggers " [<{param}>]")
        # Last element: dict whose key will be inserted before cmd.end_name
        cmd.arguments = [DummyArg("optparam", False), {"footer_label": "ignored_value"}]
        cmd.end_name = "END_MARKER"

        result = get_signature(cmd)
        expected = "mycmd [<optparam>]\nfooter_label\nEND_MARKER"
        self.assertEqual(result, expected)
