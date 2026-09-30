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
        """Test TavilySearch __init__ assigns attributes and reads API key from provided headers."""
        # Provide headers containing the tavily_api_key so get_api_key picks it up
        provided_headers = {"tavily_api_key": "TEST_KEY_123", "Some-Other": "value"}
        query = "example search"
        topic = "tech"
        query_domains = ["example.com", "other.com"]

        # Instantiate the TavilySearch object
        ts = TavilySearch(query=query, headers=provided_headers, topic=topic, query_domains=query_domains)

        # Verify that the query and topic are set correctly
        self.assertEqual(ts.query, query)
        self.assertEqual(ts.topic, topic)

        # Verify base_url is set as expected
        self.assertEqual(ts.base_url, "https://api.tavily.com/search")

        # get_api_key should have read the API key from the provided headers
        self.assertEqual(ts.api_key, "TEST_KEY_123")

        # __init__ overwrites headers to Content-Type json; ensure it's set to that value
        self.assertEqual(ts.headers, {"Content-Type": "application/json"})

        # query_domains should be preserved as given
        self.assertEqual(ts.query_domains, query_domains)
