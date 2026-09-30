import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.chat')
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
        """_get_client_params filters out None values and includes http_client when provided."""
        sentinel = object()
        model_name = "o4-mini"

        # Instance with some fields set and some left as None, and with an http_client provided.
        c = ChatOpenAI(
            model=model_name,
            api_key="sk-test-key",
            organization=None,
            project=None,
            base_url=None,
            websocket_base_url=None,
            timeout=None,
            max_retries=10,
            default_headers={"X-Test": "1"},
            default_query=None,
            http_client=sentinel,
            _strict_response_validation=True,
        )

        params = c._get_client_params()

        # Keys present and values preserved
        self.assertIn("api_key", params)
        self.assertEqual(params["api_key"], "sk-test-key")
        self.assertIn("max_retries", params)
        self.assertEqual(params["max_retries"], 10)
        self.assertIn("default_headers", params)
        self.assertEqual(params["default_headers"], {"X-Test": "1"})
        self.assertIn("_strict_response_validation", params)
        self.assertTrue(params["_strict_response_validation"])
        self.assertIn("http_client", params)
        self.assertIs(params["http_client"], sentinel)

        # Keys that were set to None should not be present
        for absent_key in (
            "organization",
            "project",
            "base_url",
            "websocket_base_url",
            "timeout",
            "default_query",
        ):
            self.assertNotIn(absent_key, params)

        # Now test instance without http_client and without api_key
        c2 = ChatOpenAI(model=model_name, api_key=None, http_client=None, max_retries=5)
        params2 = c2._get_client_params()

        # http_client and api_key were None, so they must be filtered out
        self.assertNotIn("http_client", params2)
        self.assertNotIn("api_key", params2)

        # max_retries and _strict_response_validation (default False) should be present
        self.assertIn("max_retries", params2)
        self.assertEqual(params2["max_retries"], 5)
        self.assertIn("_strict_response_validation", params2)
        self.assertFalse(params2["_strict_response_validation"])
