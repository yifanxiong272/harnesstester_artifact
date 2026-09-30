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
        """Trigger the branch where an unknown chat mode prints a tool_error message."""
        # Prepare a simple IO mock to capture outputs
        class IO:
            def __init__(self):
                self.tool_error_calls = []
                self.tool_output_calls = []

            def tool_error(self, msg=""):
                self.tool_error_calls.append(msg)

            def tool_output(self, msg=""):
                self.tool_output_calls.append(msg)

        io = IO()

        # Minimal coder object (not used by the branch we're testing)
        class DummyCoder:
            pass

        coder = DummyCoder()

        # Ensure aider.coders.__all__ has at least one edit_format so valid_formats is non-empty
        coders_mod = __import__("aider.coders", fromlist=["coders"])
        orig_all = getattr(coders_mod, "__all__", None)

        class FakeCoder:
            edit_format = "some-format"
            __doc__ = "Fake coder description\nMore lines"

        coders_mod.__all__ = [FakeCoder]

        try:
            # Instantiate Commands
            cmds_mod = __import__("aider.commands", fromlist=["Commands"])
            Commands = cmds_mod.Commands
            commands = Commands(io=io, coder=coder)

            # Call cmd_chat_mode with an unknown, non-empty mode to hit the tool_error branch
            unknown_mode = "unknown-mode"
            commands.cmd_chat_mode(unknown_mode)

            # Assert tool_error was called with the expected message (including trailing newline)
            expected_error = f'Chat mode "{unknown_mode}" should be one of these:\n'
            self.assertIn(expected_error, io.tool_error_calls)

            # Also assert that tool_output was used to list available modes
            # There should be several lines starting with "- "
            self.assertTrue(any(call.startswith("- ") for call in io.tool_output_calls))

        finally:
            # Restore original state
            if orig_all is None:
                try:
                    delattr(coders_mod, "__all__")
                except Exception:
                    pass
            else:
                coders_mod.__all__ = orig_all
