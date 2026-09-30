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
        """When cmd_chat_mode is called with an empty string it should print the available chat modes header."""
        # Prepare a simple io that captures outputs
        outputs = []

        class DummyIO:
            encoding = "utf-8"

            def tool_output(self, s=""):
                outputs.append(("out", s))

            def tool_error(self, s=""):
                outputs.append(("err", s))

            def tool_warning(self, s=""):
                outputs.append(("warn", s))

            def confirm_ask(self, *args, **kwargs):
                return False

        io = DummyIO()

        # Create a fake coder class list for aider.coders.__all__
        class FakeCoder:
            edit_format = "fakeformat"
            __doc__ = "Fake coder format\nExtra"

        # Minimal coder mock for Commands initialization
        coder = MagicMock()
        coder.main_model = MagicMock()
        coder.main_model.edit_format = "fakeformat"
        coder.get_announcements = lambda: []

        # Patch the coders.__all__ used by cmd_chat_mode
        with patch("aider.coders.__all__", [FakeCoder]):
            # Instantiate Commands and call cmd_chat_mode with empty args
            commands = Commands(io, coder)
            commands.cmd_chat_mode("")

        # Verify that the expected header message was output
        found = any("Chat mode should be one of these" in text for kind, text in outputs if kind == "out")
        self.assertTrue(found, f"Expected header not found in outputs: {outputs}")
