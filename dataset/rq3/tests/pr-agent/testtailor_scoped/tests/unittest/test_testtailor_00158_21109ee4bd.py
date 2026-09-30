import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.ai_handlers.openai_ai_handler')
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
        """Ensure OpenAIHandler reads OPENAI.API_VERSION from settings and sets openai.api_version"""
        class DummyOpenAI:
            def __init__(self):
                self.key = "sk-test"
                self.org = "org-test"
                self.api_type = "not_azure"
                self.api_version = "expected-version-123"
                self.api_base = "https://example.com/"

        class DummySettings:
            def __init__(self):
                self.openai = DummyOpenAI()

            def get(self, key, default=None):
                mapping = {
                    "OPENAI.ORG": getattr(self.openai, "org", None),
                    "OPENAI.API_TYPE": getattr(self.openai, "api_type", None),
                    "OPENAI.API_VERSION": getattr(self.openai, "api_version", None),
                    "OPENAI.API_BASE": getattr(self.openai, "api_base", None),
                    "OPENAI.DEPLOYMENT_ID": None,
                }
                return mapping.get(key, default)

        # Patch the get_settings used inside the OpenAIHandler module so the constructor picks up our dummy values
        with patch("pr_agent.algo.ai_handlers.openai_ai_handler.get_settings", return_value=DummySettings()):
            # ensure api_version is different before instantiation
            openai.api_version = None
            handler = OpenAIHandler()
            # The constructor should have set openai.api_version from settings
            self.assertEqual(openai.api_version, "expected-version-123")
