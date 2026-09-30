import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.gui')
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
        """Test that get_coder creates a CaptureIO and assigns it to coder.commands.io,
        and that announcements are forwarded to the original coder.io."""
        import importlib

        gui = importlib.import_module("aider.gui")

        # Dummy objects to stand in for real Coder and its io/commands
        class DummyIO:
            def __init__(self):
                self.dry_run = False
                self.encoding = "utf-8"
                self.outputs = []

            def tool_output(self, *messages, log_only=False, **kwargs):
                # Mimic InputOutput.tool_output behavior enough for testing
                self.outputs.append(" ".join(str(m) for m in messages))

        class DummyCommands:
            def __init__(self):
                self.io = None

        class DummyCoder:
            def __init__(self):
                self.repo = True  # non-empty repo required by get_coder
                self.io = DummyIO()
                self.commands = DummyCommands()
                self._announcements = ["announce 1", "announce 2"]

            def get_announcements(self):
                return list(self._announcements)

        # Patch gui.cli_main and gui.Coder to use our dummy versions for the test
        orig_cli_main = getattr(gui, "cli_main", None)
        orig_Coder = getattr(gui, "Coder", None)
        try:
            gui.Coder = DummyCoder
            gui.cli_main = lambda return_coder=False: DummyCoder()

            coder = gui.get_coder()

            # Returned object should be our DummyCoder instance
            self.assertIsInstance(coder, DummyCoder)

            # coder.commands.io should be set to a CaptureIO instance from the gui module
            self.assertIsNotNone(coder.commands.io)
            # The class name should match CaptureIO defined in the project
            self.assertEqual(type(coder.commands.io).__name__, "CaptureIO")
            # Ensure we did not replace the main coder.io (the function intentionally leaves it)
            self.assertIsNot(coder.commands.io, coder.io)

            # Announcements should have been sent to the original coder.io
            self.assertEqual(coder.io.outputs, coder.get_announcements())
        finally:
            # Restore patched attributes to avoid side effects on other tests
            if orig_cli_main is not None:
                gui.cli_main = orig_cli_main
            else:
                delattr(gui, "cli_main")
            if orig_Coder is not None:
                gui.Coder = orig_Coder
            else:
                delattr(gui, "Coder")
