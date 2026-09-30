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
        """Test ExaSearch.find_similar builds the response from client.find_similar results"""
        # Create an ExaSearch instance without running __init__
        exa = ExaSearch.__new__(ExaSearch)

        # Prepare a mock client with a find_similar method
        mock_client = MagicMock()
        # Create fake result objects with .url and .text attributes using MagicMock
        result_item = MagicMock()
        result_item.url = "http://example.com/similar"
        result_item.text = "Similar content"
        mock_client.find_similar.return_value = MagicMock(results=[result_item])

        # Attach the mock client to the instance
        exa.client = mock_client

        # Call the method under test
        output = exa.find_similar("http://example.com/source", exclude_source_domain=True, custom_filter="value")

        # Assertions: ensure the client was called with the expected arguments
        mock_client.find_similar.assert_called_once_with(
            "http://example.com/source", exclude_source_domain=True, custom_filter="value"
        )

        # Ensure the output matches the transformed results
        expected = [{"href": "http://example.com/similar", "body": "Similar content"}]
        self.assertEqual(output, expected)
