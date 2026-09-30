import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searchapi.searchapi')
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
        """Verify SearchApiSearch.search builds the correct request and returns processed results (skips YouTube)."""
        # Arrange: set API key env var expected by SearchApiSearch
        os.environ["SEARCHAPI_API_KEY"] = "DUMMYKEY"

        # Prepare a fake response from the Search API with a youtube result to be skipped
        fake_results = {
            "organic_results": [
                {"title": "First Result", "link": "https://example.com/1", "snippet": "First snippet"},
                {"title": "A YouTube Video", "link": "https://youtube.com/watch?v=abc", "snippet": "Should be skipped"},
                {"title": "Second Result", "link": "https://example.com/2", "snippet": "Second snippet"},
            ]
        }
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = fake_results

        # Patch requests.get so no real network call is performed
        with patch('requests.get', return_value=fake_response) as mock_get:
            # Act: create SearchApiSearch and call search
            searcher = SearchApiSearch(query="test query")
            results = searcher.search(max_results=2)

            # Assert: requests.get was called once with the encoded URL and correct headers/timeout
            expected_url = "https://www.searchapi.io/api/v1/search?q=test+query&engine=google"
            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]
            self.assertEqual(called_url, expected_url)

            called_kwargs = mock_get.call_args[1]
            self.assertIn('headers', called_kwargs)
            headers = called_kwargs['headers']
            # Check headers contain expected fields
            self.assertEqual(headers.get('Content-Type'), 'application/json')
            self.assertEqual(headers.get('Authorization'), f'Bearer DUMMYKEY')
            self.assertEqual(headers.get('X-SearchApi-Source'), 'gpt-researcher')
            self.assertEqual(called_kwargs.get('timeout'), 20)

            # The youtube result should be skipped and max_results=2 should limit results
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['title'], "First Result")
            self.assertEqual(results[0]['href'], "https://example.com/1")
            self.assertEqual(results[0]['body'], "First snippet")
            self.assertEqual(results[1]['title'], "Second Result")
            self.assertEqual(results[1]['href'], "https://example.com/2")
            self.assertEqual(results[1]['body'], "Second snippet")

        # Cleanup
        del os.environ["SEARCHAPI_API_KEY"]
