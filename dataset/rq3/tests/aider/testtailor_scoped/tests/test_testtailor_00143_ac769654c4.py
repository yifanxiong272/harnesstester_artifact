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
        """Test cmd_chat_mode lists available show_formats and valid edit formats when given an invalid mode."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch

        # Create fake coder objects with edit_format and __doc__
        class FakeCoder:
            def __init__(self, edit_format, doc):
                self.edit_format = edit_format
                self.__doc__ = doc

        fake_coder_1 = FakeCoder("fmt_one", "Formatter one description\nmore details")
        fake_coder_2 = FakeCoder("fmt_two", "Formatter two description")

        # Simple IO collector to capture outputs/errors
        class CollectIO:
            def __init__(self):
                self.outputs = []
                self.errors = []
                self.encoding = "utf-8"

            def tool_output(self, s=""):
                # mimic behavior when called with no args
                if s is None:
                    s = ""
                self.outputs.append(s)

            def tool_error(self, s=""):
                self.errors.append(s)

            def tool_warning(self, s=""):
                self.outputs.append(s)

        io = CollectIO()
        coder_mock = MagicMock()
        # Provide a main_model in case it's accessed elsewhere (not needed for this test path)
        coder_mock.main_model = MagicMock(edit_format="fmt_one")

        # Patch the coders.__all__ used by cmd_chat_mode to include our fake coders
        with patch("aider.coders.__all__", new=[fake_coder_1, fake_coder_2]):
            # Import Commands here to ensure it uses the patched coders.__all__
            from aider.commands import Commands

            cmd = Commands(io, coder_mock)

            # Call with an invalid/unknown chat mode to trigger the listing behavior
            cmd.cmd_chat_mode("unknown-mode")

        combined = "\n".join(io.errors + io.outputs)

        # Expect an error message about the unknown chat mode
        self.assertIn('Chat mode "unknown-mode" should be one of these:', combined)

        # Expect the show_formats to be listed (help, ask, code, architect, context)
        self.assertIn("- help", combined)
        self.assertIn("- ask", combined)
        self.assertIn("- code", combined)
        self.assertIn("- architect", combined)
        self.assertIn("- context", combined)

        # Expect our valid edit formats (from fake coders) to be listed
        self.assertIn("fmt_one", combined)
        self.assertIn("fmt_two", combined)
