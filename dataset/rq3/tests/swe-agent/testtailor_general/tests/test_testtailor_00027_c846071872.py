import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.tools')
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
        """Ensure duplicate command names across bundles raise a clear ValueError."""
        # Create a minimal dummy bundle class to hold commands and a path
        class DummyBundle:
            def __init__(self, commands, path):
                self.commands = commands
                self.path = path

        # Two commands with the same name to trigger the duplicate detection
        cmd1 = Command(name="duplicate_cmd", docstring="first definition")
        cmd2 = Command(name="duplicate_cmd", docstring="second definition")

        b1 = DummyBundle([cmd1], Path("bundle_one.yaml"))
        b2 = DummyBundle([cmd2], Path("bundle_two.yaml"))

        cfg = ToolConfig()  # default config
        # Bypass pydantic validation by setting bundles directly in __dict__
        cfg.__dict__["bundles"] = [b1, b2]
        # Ensure any cached value for commands is cleared so the property recomputes
        if "commands" in cfg.__dict__:
            del cfg.__dict__["commands"]

        with self.assertRaises(ValueError) as cm:
            _ = cfg.commands  # access triggers the logic that should raise

        msg = str(cm.exception)
        self.assertIn("Tool 'duplicate_cmd' is defined multiple times", msg)
        self.assertIn("First definition in: bundle_one.yaml", msg)
        self.assertIn("Duplicate definition in: bundle_two.yaml", msg)
