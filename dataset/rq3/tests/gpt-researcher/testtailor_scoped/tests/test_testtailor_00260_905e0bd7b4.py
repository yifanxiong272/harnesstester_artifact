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
        """Ensure query_domains are appended to the search query as 'site:domain1 OR site:domain2'."""
        # Ensure API key is present so get_api_key does not raise
        os.environ["SERPAPI_API_KEY"] = "dummy_key"

        # Prepare a fake HTTP response for requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic_results": [
                {"title": "Result 1", "link": "http://example.com/page1", "snippet": "Snippet 1"},
                {"title": "Result 2", "link": "http://youtube.com/watch?v=abc", "snippet": "YouTube result should be skipped"},
                {"title": "Result 3", "link": "http://test.org/page2", "snippet": "Snippet 2"},
            ]
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
            # Instantiate with query_domains to hit the target branch
            searcher = SerpApiSearch(query="my query", query_domains=["example.com", "test.org"])

            results = searcher.search(max_results=5)

            # Verify requests.get was called and that the encoded URL contains both domains as site:... parts
            self.assertTrue(mock_get.called)
            called_url = mock_get.call_args[0][0]
            # URL will be encoded; check for encoded site: occurrences
            self.assertIn("site%3Aexample.com", called_url)
            self.assertIn("site%3Atest.org", called_url)

            # Verify results: youtube result should be skipped, so we should get 2 valid results (example.com and test.org)
            self.assertEqual(len(results), 2)
            titles = [r["title"] for r in results]
            self.assertIn("Result 1", titles)
            self.assertIn("Result 3", titles)
