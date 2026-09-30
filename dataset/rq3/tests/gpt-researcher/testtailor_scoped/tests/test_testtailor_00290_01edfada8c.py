import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.tavily.tavily_search')
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
        """Test that TavilySearch._search builds the correct payload and calls requests.post"""
        with patch("requests.post") as mock_post:
            # Prepare mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [{"url": "http://example.com", "content": "hello"}]
            }
            mock_post.return_value = mock_response

            # Initialize TavilySearch with an explicit API key via headers so get_api_key picks it up
            ts = TavilySearch("my query", headers={"tavily_api_key": "FAKE_KEY"}, topic="technology", query_domains=["example.com"])

            # Call the internal _search with a variety of parameters to exercise the payload creation
            result = ts._search(
                query="my query",
                search_depth="advanced",
                topic="technology",
                days=5,
                max_results=3,
                include_domains=["example.com"],
                exclude_domains=["exclude.com"],
                include_answer=True,
                include_raw_content=False,
                include_images=True,
                use_cache=False,
            )

            # Verify the return value comes from response.json()
            self.assertEqual(result, mock_response.json.return_value)

            # Verify requests.post was called exactly once
            mock_post.assert_called_once()

            # Inspect the call arguments to requests.post
            call_args = mock_post.call_args
            args, kwargs = call_args

            # First positional arg should be the base_url
            self.assertEqual(args[0], ts.base_url)

            # Headers passed should match the instance headers set in __init__
            self.assertEqual(kwargs["headers"], {"Content-Type": "application/json"})

            # Timeout should be 100 as in the implementation
            self.assertEqual(kwargs["timeout"], 100)

            # The data payload should be a JSON string that matches the expected dict
            sent_data = json.loads(kwargs["data"])
            expected_data = {
                "query": "my query",
                "search_depth": "advanced",
                "topic": "technology",
                "days": 5,
                "include_answer": True,
                "include_raw_content": False,
                "max_results": 3,
                "include_domains": ["example.com"],
                "exclude_domains": ["exclude.com"],
                "include_images": True,
                "api_key": "FAKE_KEY",
                "use_cache": False,
            }
            self.assertDictEqual(sent_data, expected_data)
