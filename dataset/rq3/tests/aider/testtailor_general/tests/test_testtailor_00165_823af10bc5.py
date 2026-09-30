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
        """Verify cmd_chat_mode lists available chat modes when called with empty args and
        that it builds valid_formats from aider.coders.__all__ entries."""
        # Create fake coder-like objects with edit_format and __doc__
        fake_coder1 = MagicMock()
        fake_coder1.edit_format = "py"
        fake_coder1.__doc__ = "Python mode\nMore details"

        fake_coder2 = MagicMock()
        fake_coder2.edit_format = "sql"
        fake_coder2.__doc__ = None  # should be displayed as "No description"

        # Patch the coders module's __all__ to include our fake coders
        with patch("aider.coders.__all__", [fake_coder1, fake_coder2]):
            io = MagicMock()
            coder = MagicMock()
            # Instantiate Commands (assumes Commands is available in test context)
            cmds = Commands(io, coder)

            # Call with empty string to trigger the "list available chat modes" branch
            cmds.cmd_chat_mode("")

            # Verify that the high-level prompt was printed
            io.tool_output.assert_any_call("Chat mode should be one of these:\n")

            # Collect all outputs to verify that both show_formats and valid_formats were printed
            outputs = [call.args[0] for call in io.tool_output.call_args_list]

            # show_formats should include 'ask'
            self.assertTrue(any("ask" in o for o in outputs), "Expected 'ask' in displayed formats")

            # our fake coder edit formats should be present in the valid formats listing
            self.assertTrue(any("py" in o for o in outputs), "Expected 'py' (from fake coder) in output")
            self.assertTrue(any("sql" in o for o in outputs), "Expected 'sql' (from fake coder) in output")
