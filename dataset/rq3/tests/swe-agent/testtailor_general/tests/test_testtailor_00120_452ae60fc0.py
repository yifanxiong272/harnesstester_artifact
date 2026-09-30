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
        """ToolHandler.from_config returns an instance of the class and deep-copies the config."""
        cfg = ToolConfig()
        handler = ToolHandler.from_config(cfg)

        # Correct type
        self.assertIsInstance(handler, ToolHandler)

        # The handler should have copied the config (not the same object) but equal content
        self.assertIsNot(handler.config, cfg)
        self.assertEqual(handler.config.model_dump(), cfg.model_dump())

        # Internal attributes set up by __init__
        self.assertIsInstance(handler._reset_commands, list)
        self.assertIsInstance(handler._command_patterns, dict)

        # from_config should respect subclassing (returns instance of the subclass)
        class MyHandler(ToolHandler):
            pass

        sub = MyHandler.from_config(cfg)
        self.assertIsInstance(sub, MyHandler)
