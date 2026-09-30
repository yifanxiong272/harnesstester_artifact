import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.openalex.openalex')
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
        """Test that search reconstructs title, href, and abstract correctly for a result."""
        # Prepare a result with no title, a best_oa_location pdf_url, and an inverted abstract index
        result = {
            # 'title' intentionally omitted to trigger the "No Title" fallback
            "best_oa_location": {"pdf_url": "http://example.com/test.pdf"},
            "primary_location": {"landing_page_url": "http://example.com/landing"},
            "id": "https://openalex.org/W1234567890",
            "abstract_inverted_index": {
                "Hello": [0],
                "world": [1]
            },
        }

        # Mock requests.get to return our crafted response
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [result]}
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response) as mock_get:
            searcher = OpenAlexSearch(query="test query")
            results = searcher.search(max_results=1)

            # Ensure requests.get was called with expected parameters
            mock_get.assert_called_once()
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)

            item = results[0]
            # Title should fall back to "No Title"
            self.assertEqual(item["title"], "No Title")
            # href should prefer the pdf_url from best_oa_location
            self.assertEqual(item["href"], "http://example.com/test.pdf")
            # abstract should be reconstructed from the inverted index
            self.assertEqual(item["body"], "Hello world")
