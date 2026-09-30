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
        """Ensure TavilySearch.__init__ sets attributes and reads API key from provided headers,
        and that headers are later overwritten to only contain Content-Type."""
        # Arrange: provide a headers dict that includes the tavily_api_key
        provided_headers = {"tavily_api_key": "APIKEY123", "X-Custom": "value"}
        query_domains = ["example.com", "another.com"]

        # Act: instantiate TavilySearch
        ts = TavilySearch(query="test query", headers=provided_headers, topic="science", query_domains=query_domains)

        # Assert: basic attributes set from constructor args
        self.assertEqual(ts.query, "test query")
        self.assertEqual(ts.topic, "science")
        self.assertEqual(ts.base_url, "https://api.tavily.com/search")

        # Assert: api_key was retrieved from the initial headers passed to __init__
        self.assertEqual(ts.api_key, "APIKEY123")

        # Assert: headers were overwritten inside __init__ to only Content-Type
        self.assertEqual(ts.headers, {"Content-Type": "application/json"})

        # Assert: query_domains preserved as provided
        self.assertEqual(ts.query_domains, query_domains)
