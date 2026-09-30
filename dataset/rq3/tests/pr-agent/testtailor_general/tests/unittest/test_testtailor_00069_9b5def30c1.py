import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.mosaico.executor')
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
        """Verify that when LiteLLMAIHandler.api_base is set, health_check passes it to litellm.acompletion."""
        # Dynamically import needed modules to avoid top-level import statements in this snippet
        sys = __import__("sys")
        types = __import__("types")
        mock = __import__("unittest.mock", fromlist=["patch"])
        patch = mock.patch
        asyncio = __import__("asyncio")

        # Prepare a fake settings object that returns a model name
        class FakeSettings:
            def get(self, key, default=None):
                if key == "CONFIG.MODEL":
                    return "test-model"
                return default

        fake_settings = FakeSettings()

        # Fake handler class with a non-None api_base attribute
        class FakeHandler:
            def __init__(self):
                self.api_base = "https://example.api/"

        # Prepare a fake litellm module with an async acompletion that captures kwargs
        called = {}
        async def fake_acompletion(**kwargs):
            called["kwargs"] = kwargs
            return "ok"

        fake_litellm = types.ModuleType("litellm")
        fake_litellm.acompletion = fake_acompletion

        # Patch get_settings and the LiteLLMAIHandler, and inject the fake litellm module
        with patch("pr_agent.config_loader.get_settings", return_value=fake_settings):
            with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.LiteLLMAIHandler", FakeHandler):
                orig_litellm = sys.modules.get("litellm")
                sys.modules["litellm"] = fake_litellm
                try:
                    result = asyncio.run(health_check())
                finally:
                    # restore original litellm module if any
                    if orig_litellm is None:
                        del sys.modules["litellm"]
                    else:
                        sys.modules["litellm"] = orig_litellm

        # Assertions: health_check should succeed and pass api_base through to acompletion
        self.assertEqual(result, "OK")
        self.assertIn("kwargs", called)
        self.assertIn("api_base", called["kwargs"])
        self.assertEqual(called["kwargs"]["api_base"], "https://example.api/")
