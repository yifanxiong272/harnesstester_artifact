import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serper.serper')
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
    @patch('requests.request')
    @timeout_decorator.timeout(1)
    def test_case_XX(self, mock_request):
        """Test SerperSearch.search builds correct query, headers, and normalizes results."""
        # Ensure API key present for SerperSearch.get_api_key
        os.environ['SERPER_API_KEY'] = 'test-key-123'

        # Prepare a fake response from the Serper API
        fake_resp = MagicMock()
        fake_resp.text = json.dumps({
            "organic": [
                {"title": "Result Title", "link": "https://example.com/page", "snippet": "A short snippet"}
            ]
        })
        mock_request.return_value = fake_resp

        # Instantiate SerperSearch with domains and excluded sites to exercise query building
        serper = SerperSearch(
            query="my test query",
            query_domains=["example.com", "test.com"],
            exclude_sites=["bad.com"],
            country="us",
            language="en",
            time_range="qdr:m"
        )

        # Call search and capture results
        results = serper.search(max_results=5)

        # Verify the requests.request was called correctly
        mock_request.assert_called_once()
        # Inspect kwargs passed to requests.request
        call_kwargs = mock_request.call_args.kwargs

        # Check headers include the API key
        self.assertIn('headers', call_kwargs)
        self.assertEqual(call_kwargs['headers']['X-API-KEY'], os.environ['SERPER_API_KEY'])
        self.assertEqual(call_kwargs['headers']['Content-Type'], 'application/json')

        # Check timeout was provided
        self.assertEqual(call_kwargs.get('timeout'), 10)

        # Verify the posted data contains the expected search parameters
        posted = json.loads(call_kwargs['data'])
        self.assertEqual(posted['num'], 5)
        # Query should include original query, excluded site, and domain filtering
        self.assertIn("my test query", posted['q'])
        self.assertIn("-site:bad.com", posted['q'])
        self.assertIn("site:example.com OR site:test.com", posted['q'])
        # Optional parameters should be present
        self.assertEqual(posted.get('gl'), 'us')
        self.assertEqual(posted.get('hl'), 'en')
        self.assertEqual(posted.get('tbs'), 'qdr:m')

        # Verify the returned results are normalized as expected
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Result Title")
        self.assertEqual(results[0]['href'], "https://example.com/page")
        self.assertEqual(results[0]['body'], "A short snippet")

        # Cleanup
        del os.environ['SERPER_API_KEY']
