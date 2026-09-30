import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bocha.bocha')
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
        """Test BoChaSearch.search posts correct request and normalizes results."""
        # Ensure API key exists for initializer
        os.environ["BOCHA_API_KEY"] = "fake_key"

        # Prepare mock response JSON structure expected by the method
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "webPages": {
                    "value": [
                        {"name": "Title 1", "url": "http://a", "snippet": "Snippet 1"},
                        {"name": "Title 2", "url": "http://b", "snippet": "Snippet 2"},
                    ]
                }
            }
        }

        # Patch requests.post to return our mock response
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response

            # Instantiate and call the search method
            retriever = BoChaSearch(query="hello")
            results = retriever.search(max_results=2)

            # Verify requests.post was called with expected URL and payload
            mock_post.assert_called_once()
            called_args, called_kwargs = mock_post.call_args
            self.assertEqual(called_args[0], 'https://api.bochaai.com/v1/web-search')

            # Check headers
            self.assertIn('headers', called_kwargs)
            headers = called_kwargs['headers']
            self.assertIn('Authorization', headers)
            self.assertTrue(headers['Authorization'].startswith('Bearer fake_key'))
            self.assertEqual(headers.get('Content-Type'), 'application/json')

            # Check JSON body
            self.assertIn('json', called_kwargs)
            body = called_kwargs['json']
            self.assertEqual(body['query'], 'hello')
            self.assertEqual(body['count'], 2)
            self.assertTrue(body['summary'])
            self.assertEqual(body['freshness'], 'noLimit')

            # Verify the returned results are normalized correctly
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]['title'], 'Title 1')
            self.assertEqual(results[0]['href'], 'http://a')
            self.assertEqual(results[0]['body'], 'Snippet 1')
            self.assertEqual(results[1]['title'], 'Title 2')
            self.assertEqual(results[1]['href'], 'http://b')
            self.assertEqual(results[1]['body'], 'Snippet 2')
