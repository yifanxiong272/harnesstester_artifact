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
    def test_case_XX(self):
        """When switching to 'code' chat mode, the edit_format should come from the main_model
        and summarize_from_coder should be False (SwitchCoder raised with those kwargs)."""
        io = MagicMock()
        coder = MagicMock()
        # Set the main_model's edit_format to a known value
        main_model = MagicMock()
        main_model.edit_format = "main-model-format"
        coder.main_model = main_model

        cmds = Commands(io, coder)

        # Ensure coders.__all__ doesn't interfere with building valid_formats
        with patch("aider.coders.__all__", []):
            with self.assertRaises(SwitchCoder) as cm:
                cmds.cmd_chat_mode("code")

        exc = cm.exception
        self.assertIn("edit_format", exc.kwargs)
        self.assertIn("summarize_from_coder", exc.kwargs)
        self.assertEqual(exc.kwargs["edit_format"], "main-model-format")
        self.assertFalse(exc.kwargs["summarize_from_coder"])
