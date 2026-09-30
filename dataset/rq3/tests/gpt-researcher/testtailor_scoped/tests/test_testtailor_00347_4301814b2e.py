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
        """Test that ExaSearch.get_contents calls client.get_contents and formats results correctly"""
        # Create an ExaSearch instance without running __init__
        exa_search = ExaSearch.__new__(ExaSearch)

        # Prepare a mock client and fake response objects
        mock_client = MagicMock()

        class FakeResult:
            def __init__(self, id, text):
                self.id = id
                self.text = text

        fake_results = [FakeResult("doc1", "content one"), FakeResult("doc2", "content two")]
        mock_response = MagicMock()
        mock_response.results = fake_results
        mock_client.get_contents.return_value = mock_response

        # Attach the mock client to the ExaSearch instance
        exa_search.client = mock_client

        # Call the method under test
        ids = ["doc1", "doc2"]
        options = {"include_text": True}
        contents = exa_search.get_contents(ids, **options)

        # Verify the client was called with the same args and the output is formatted correctly
        mock_client.get_contents.assert_called_once_with(ids, **options)
        expected = [
            {"id": "doc1", "content": "content one"},
            {"id": "doc2", "content": "content two"},
        ]
        self.assertEqual(contents, expected)
