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
        """Exercise BingSearch.search path that builds headers/params and calls requests.get"""
        # Ensure API key is present for get_api_key()
        os.environ["BING_API_KEY"] = "testkey"
        try:
            # Prepare a BingSearch instance
            bs = BingSearch(query="my query")

            # Mock the requests.get response to contain two results, one of which is a youtube link (should be skipped)
            mock_resp = MagicMock()
            mock_resp.text = json.dumps({
                "webPages": {
                    "value": [
                        {"name": "Title1", "url": "http://example.com/page1", "snippet": "Snippet1"},
                        {"name": "YT Video", "url": "https://youtube.com/watch?v=abc", "snippet": "YouTube Snippet"}
                    ]
                }
            })

            url = "https://api.bing.microsoft.com/v7.0/search"

            # Patch requests.get so no real HTTP call is made
            with patch('requests.get', return_value=mock_resp) as mock_get:
                results = bs.search(max_results=5)

            # Verify the results: only the non-youtube result is returned and normalized
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Title1")
            self.assertEqual(results[0]["href"], "http://example.com/page1")
            self.assertEqual(results[0]["body"], "Snippet1")

            # Verify requests.get was called correctly with url, headers and params
            mock_get.assert_called_once()
            called_args, called_kwargs = mock_get.call_args
            # first positional arg should be the URL
            self.assertEqual(called_args[0], url)
            # headers should include our subscription key
            self.assertIn('headers', called_kwargs)
            self.assertEqual(called_kwargs['headers']['Ocp-Apim-Subscription-Key'], "testkey")
            # params should include the query and count we passed
            self.assertIn('params', called_kwargs)
            self.assertEqual(called_kwargs['params']['q'], "my query")
            self.assertEqual(called_kwargs['params']['count'], 5)
        finally:
            # Cleanup env var to avoid side effects
            try:
                del os.environ["BING_API_KEY"]
            except KeyError:
                pass
