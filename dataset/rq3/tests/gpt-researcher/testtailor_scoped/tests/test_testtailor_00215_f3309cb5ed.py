import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.xquik.xquik')
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
        """Verify that calling search prints the expected message and delegates to _search_tweets."""
        # Ensure API key lookup succeeds
        os.environ["XQUIK_API_KEY"] = "dummy_key"

        # Prepare a fake return value for _search_tweets
        fake_results = [
            {"title": "@alice: hello", "href": "https://x.com/alice/status/1", "body": "hello\n\n[1 likes, 0 RTs]"}
        ]

        searcher = XquikSearch(query="hello")

        # Patch the internal _search_tweets to avoid network I/O and patch print to capture output
        with patch.object(XquikSearch, "_search_tweets", return_value=fake_results) as mock_search, \
             patch('builtins.print') as mock_print:
            results = searcher.search(max_results=5)

        # Assertions
        mock_search.assert_called_once_with(5)
        self.assertEqual(results, fake_results)
        mock_print.assert_any_call("Searching X/Twitter with query: hello...")
