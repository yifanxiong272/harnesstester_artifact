import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.anthropic.chat')
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
        """Ensure _get_client_params filters out None values (and handles NotGiven default)."""
        # Provide required model param when constructing
        model = ChatAnthropic(model="claude-2")
        # Set attributes to test filtering behavior
        model.api_key = None  # should be filtered out
        model.auth_token = "auth_tok"  # should be present
        model.base_url = "https://example.com"  # should be present
        model.timeout = None  # explicitly set to None so it is filtered out
        model.max_retries = 5  # should be present
        model.default_headers = {"hdr": "v"}  # should be present
        model.default_query = None  # should be filtered out
        model.http_client = "http_client_obj"  # should be present

        client_params = model._get_client_params()

        expected = {
            "auth_token": "auth_tok",
            "base_url": "https://example.com",
            "max_retries": 5,
            "default_headers": {"hdr": "v"},
            "http_client": "http_client_obj",
        }

        self.assertEqual(client_params, expected)
