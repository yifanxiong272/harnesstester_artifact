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
        """Ensure ToolHandler.from_config constructs a ToolHandler and deep-copies the ToolConfig."""
        # create a ToolConfig with a mutable field we can mutate later
        cfg = ToolConfig()
        cfg.reset_commands = ["echo initial"]

        handler = ToolHandler.from_config(cfg)

        # returned object is a ToolHandler
        self.assertIsInstance(handler, ToolHandler)

        # handler.config is a copy, not the same object
        self.assertIsNot(handler.config, cfg)

        # values are initially the same
        self.assertEqual(handler.config.reset_commands, ["echo initial"])

        # modifying the original config should not affect the handler's config (deep copy)
        cfg.reset_commands.append("echo modified")
        self.assertNotEqual(handler.config.reset_commands, cfg.reset_commands)

        # internal initialization performed in __init__ (e.g., _reset_commands present)
        self.assertIsInstance(handler._reset_commands, list)

        # command patterns should include the builtin bash command by default
        self.assertIn("bash", handler._command_patterns)
