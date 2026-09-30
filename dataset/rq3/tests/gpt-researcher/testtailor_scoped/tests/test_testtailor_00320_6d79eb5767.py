import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bing.bing')
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
        """Test BingSearch.search logs an error and returns empty list when 'webPages' key is missing after JSON parsing"""
        # Prepare a response with valid JSON but missing the 'webPages' key to trigger KeyError inside try block
        mock_resp = MagicMock()
        mock_resp.text = '{"someOtherKey": {"value": []}}'

        # Ensure BingSearch does not try to read real env var for API key
        with patch.object(BingSearch, "get_api_key", return_value="fake_key"):
            bing = BingSearch("test query")

        # Replace the logger with a mock to capture error calls
        bing.logger = MagicMock()

        # Patch requests.get to return our crafted response
        with patch("requests.get", return_value=mock_resp):
            result = bing.search(max_results=5)

        # Verify that an empty list is returned and an error was logged due to missing 'webPages' key
        self.assertEqual(result, [])
        bing.logger.error.assert_called_once()
        logged_msg = bing.logger.error.call_args[0][0]
        self.assertIn("Error parsing Bing search results", logged_msg)
