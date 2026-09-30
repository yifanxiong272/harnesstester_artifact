import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searx.searx')
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
        """Test that SearxSearch.search builds the correct URL/params and parses results."""
        # Ensure SEARX_URL is set (no trailing slash to exercise normalization)
        os.environ["SEARX_URL"] = "https://searx.example.com"

        # Prepare a fake response object for requests.get
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {"url": "http://example.com/page", "content": "Example content"}
            ]
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            # Instantiate the SearxSearch and call .search()
            searx = SearxSearch(query="test query")
            results = searx.search(max_results=1)

            # Validate returned results
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["href"], "http://example.com/page")
            self.assertEqual(results[0]["body"], "Example content")

            # Validate that requests.get was called with the expected URL and params
            expected_url = "https://searx.example.com/search"
            expected_params = {"q": "test query", "format": "json"}
            mock_get.assert_called_once_with(
                expected_url,
                params=expected_params,
                headers={"Accept": "application/json"}
            )

        # Clean up environment variable
        del os.environ["SEARX_URL"]
