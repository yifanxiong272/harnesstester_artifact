import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """Test that Preselector.__init__ uses get_model with a ToolConfig that has an ActionParser
        and that get_logger is called with the expected name and emoji.
        """
        # create a simple fake config object (no need to use Pydantic here)
        class FakeConfig:
            pass

        cfg = FakeConfig()
        cfg.model = object()
        cfg.system_template = "system"
        cfg.instance_template = "instance"
        cfg.submission_template = "submission"
        cfg.max_len_submission = 123

        calls = {}

        def fake_get_model(model_arg, tool_config):
            # record arguments for assertions
            calls["model_arg"] = model_arg
            calls["tool_config"] = tool_config
            return "FAKE_MODEL_OBJ"

        def fake_get_logger(name, *, emoji=""):
            calls["logger_name"] = name
            calls["logger_emoji"] = emoji
            return "FAKE_LOGGER_OBJ"

        # Patch the globals used by Preselector.__init__ to use our fakes
        real_get_model = Preselector.__init__.__globals__.get("get_model")
        real_get_logger = Preselector.__init__.__globals__.get("get_logger")
        try:
            Preselector.__init__.__globals__["get_model"] = fake_get_model
            Preselector.__init__.__globals__["get_logger"] = fake_get_logger

            p = Preselector(cfg)
        finally:
            # restore originals to avoid side effects on other tests
            Preselector.__init__.__globals__["get_model"] = real_get_model
            Preselector.__init__.__globals__["get_logger"] = real_get_logger

        # Assertions about assignment
        self.assertIs(p.config, cfg)
        self.assertEqual(p.model, "FAKE_MODEL_OBJ")
        self.assertEqual(p.logger, "FAKE_LOGGER_OBJ")

        # Assertions about calls to get_model and get_logger
        self.assertIs(calls.get("model_arg"), cfg.model)
        self.assertIn("tool_config", calls)
        self.assertTrue(isinstance(calls["tool_config"], ToolConfig))
        self.assertTrue(isinstance(calls["tool_config"].parse_function, ActionParser))
        self.assertEqual(calls.get("logger_name"), "chooser")
        self.assertEqual(calls.get("logger_emoji"), "🧠")
