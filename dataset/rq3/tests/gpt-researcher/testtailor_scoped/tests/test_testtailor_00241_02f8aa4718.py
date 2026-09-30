import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.exa.exa')
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
        # Prepare mock result objects
        res1 = MagicMock()
        res1.url = "http://a.com"
        res1.text = "Text A"
        res2 = MagicMock()
        res2.url = "http://b.com"
        res2.text = "Text B"

        # Mock the container returned by the client's search method
        results_container = MagicMock()
        results_container.results = [res1, res2]

        # Mock client with a search method
        mock_client = MagicMock()
        mock_client.search.return_value = results_container

        # Instantiate ExaSearch without running __init__ to avoid external dependencies
        exa = ExaSearch.__new__(ExaSearch)
        exa.client = mock_client
        exa.query = "my query"
        exa.query_domains = ["example.com"]

        # Call the method under test with additional filters
        response = exa.search(max_results=2, use_autoprompt=True, search_type="keyword", extra_filter="value")

        # Verify the client.search call received the expected parameters
        mock_client.search.assert_called_once_with(
            "my query",
            type="keyword",
            use_autoprompt=True,
            num_results=2,
            include_domains=["example.com"],
            extra_filter="value",
        )

        # Verify the returned structure matches the expected transformation
        expected = [
            {"href": "http://a.com", "body": "Text A"},
            {"href": "http://b.com", "body": "Text B"},
        ]
        self.assertEqual(response, expected)
