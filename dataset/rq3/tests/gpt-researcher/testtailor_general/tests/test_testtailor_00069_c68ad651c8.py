import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.tavily_extract.tavily_extract')
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
        """Ensure TavilyExtract __init__ sets attributes and instantiates TavilyClient with env API key."""
        fake_api_key = "fake-api-key-123"
        link_value = "http://example.com"
        session_value = object()

        sys_mod = __import__("sys")
        types_mod = __import__("types")
        os_mod = __import__("os")

        original_tavily = sys_mod.modules.get("tavily")
        original_env = os_mod.environ.get("TAVILY_API_KEY")

        try:
            # Insert fake module
            fake_mod = types_mod.ModuleType("tavily")

            class FakeTavilyClient:
                def __init__(self, api_key=None):
                    self.api_key = api_key

            fake_mod.TavilyClient = FakeTavilyClient
            sys_mod.modules["tavily"] = fake_mod

            # Set environment variable so get_api_key() finds it
            os_mod.environ["TAVILY_API_KEY"] = fake_api_key

            # Instantiate the class under test
            te = TavilyExtract(link_value, session=session_value)

            # Assertions: attributes set correctly and TavilyClient received the API key
            self.assertEqual(te.link, link_value)
            self.assertIs(te.session, session_value)
            self.assertIsInstance(te.tavily_client, FakeTavilyClient)
            self.assertEqual(te.tavily_client.api_key, fake_api_key)

        finally:
            # Restore environment and modules
            if original_tavily is None:
                # remove the fake module we inserted
                if "tavily" in sys_mod.modules:
                    del sys_mod.modules["tavily"]
            else:
                sys_mod.modules["tavily"] = original_tavily

            if original_env is None:
                os_mod.environ.pop("TAVILY_API_KEY", None)
            else:
                os_mod.environ["TAVILY_API_KEY"] = original_env
