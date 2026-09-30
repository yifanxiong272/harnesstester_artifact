import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.google.google')
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
        """Verify search() returns normalized results when no query_domains are provided,
        exercising the path where search_query = self.query."""
        # Prepare a fake successful HTTP response from Google's Custom Search API
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps({
            "items": [
                {
                    "title": "Example Title",
                    "link": "https://example.com/page",
                    "snippet": "Example snippet of the page"
                }
            ]
        })

        # Patch requests.get to return our fake response
        with patch('requests.get', return_value=mock_resp) as mock_get:
            # Provide headers to avoid environment variable lookups in __init__
            gs = GoogleSearch(query="example query", headers={
                "google_api_key": "dummy_key",
                "google_cx_key": "dummy_cx"
            })

            results = gs.search(max_results=7)

            # Ensure requests.get was called and results are normalized correctly
            mock_get.assert_called_once()
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Example Title")
            self.assertEqual(results[0]["href"], "https://example.com/page")
            self.assertEqual(results[0]["body"], "Example snippet of the page")
