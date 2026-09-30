import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.commands')
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
    def test_cmd_chat_mode_sets_defaults(self):
        io = MagicMock()
        coder = MagicMock()
        commands = Commands(io, coder)

        with self.assertRaises(SwitchCoder) as cm:
            commands.cmd_chat_mode("architect")

        exc = cm.exception
        # The handler should raise SwitchCoder with the chosen edit_format
        self.assertIn("edit_format", exc.kwargs)
        self.assertIn("summarize_from_coder", exc.kwargs)
        self.assertEqual(exc.kwargs["edit_format"], "architect")
        self.assertTrue(exc.kwargs["summarize_from_coder"])
