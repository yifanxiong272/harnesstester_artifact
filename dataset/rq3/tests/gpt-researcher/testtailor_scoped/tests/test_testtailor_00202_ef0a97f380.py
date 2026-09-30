import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serpapi.serpapi')
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
        """Verify SerpApiSearch.search builds the URL and returns processed organic results when no query_domains."""
        # Ensure API key is available for get_api_key
        os.environ['SERPAPI_API_KEY'] = 'TESTKEY'

        fake_json = {
            "organic_results": [
                {"title": "Test Title", "link": "http://example.com", "snippet": "Desc"},
            ]
        }

        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = fake_json
            mock_get.return_value = mock_resp

            # Instantiate and run search without query_domains so search_query == self.query
            s = SerpApiSearch(query="my query")
            results = s.search(max_results=1)

            # Verify results processed correctly
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Test Title")
            self.assertEqual(results[0]["href"], "http://example.com")
            self.assertEqual(results[0]["body"], "Desc")

            # Verify requests.get was called with an encoded URL containing the query and API key
            called_url = mock_get.call_args[0][0]
            self.assertTrue(called_url.startswith("https://serpapi.com/search.json"))
            self.assertIn("q=my+query", called_url)
            self.assertIn("api_key=TESTKEY", called_url)
