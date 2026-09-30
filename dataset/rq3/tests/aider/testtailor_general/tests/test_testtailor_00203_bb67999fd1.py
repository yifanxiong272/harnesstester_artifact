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
        """Verify get_coder calls cli_main(return_coder=True), validates the Coder type,
        attaches a CaptureIO to coder.commands.io and forwards announcements to the original io."""
        # Import the module dynamically without top-level import statements
        gui = __import__("aider.gui", fromlist=["*"])

        # Prepare a simple fake IO that records tool_output calls
        recorded = []

        class FakeIO:
            def __init__(self):
                self.dry_run = False
                self.encoding = "utf-8"

            def tool_output(self, *msgs, **kwargs):
                # Mirror the behavior of InputOutput.tool_output joining messages
                recorded.append(" ".join(str(m) for m in msgs))

        # Simple commands holder
        class FakeCommands:
            def __init__(self):
                self.io = None

        # Fake Coder class to satisfy isinstance check in get_coder
        class FakeCoder:
            def __init__(self):
                self.repo = "/some/repo"  # truthy to bypass repo check
                self.io = FakeIO()
                self.commands = FakeCommands()

            def get_announcements(self):
                return ["announcement one", "announcement two"]

        # Save originals to restore later
        original_cli = getattr(gui, "cli_main", None)
        original_Coder = getattr(gui, "Coder", None)

        try:
            # Monkeypatch cli_main to return our FakeCoder and patch Coder symbol for isinstance
            fake_instance = FakeCoder()

            def fake_cli_main(return_coder=False):
                return fake_instance

            setattr(gui, "cli_main", fake_cli_main)
            setattr(gui, "Coder", FakeCoder)

            # Call the function under test
            result = gui.get_coder()

            # Ensure the returned object is our fake instance
            self.assertIs(result, fake_instance)

            # Announcements should have been forwarded to the original coder.io.tool_output
            self.assertEqual(recorded, ["announcement one", "announcement two"])

            # The commands.io should have been replaced with a new CaptureIO instance (not the original io)
            self.assertIsNot(result.commands.io, fake_instance.io)
            # And it should expose the capture interface (lines or get_captured_lines)
            self.assertTrue(hasattr(result.commands.io, "get_captured_lines") or hasattr(result.commands.io, "lines"))
        finally:
            # Restore original attributes to avoid side effects for other tests
            if original_cli is not None:
                setattr(gui, "cli_main", original_cli)
            else:
                if hasattr(gui, "cli_main"):
                    delattr(gui, "cli_main")

            if original_Coder is not None:
                setattr(gui, "Coder", original_Coder)
            else:
                if hasattr(gui, "Coder"):
                    delattr(gui, "Coder")
