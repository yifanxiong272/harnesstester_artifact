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
        """Ensure search params use min(max_results, 25) and include optional env keys."""
        # Set environment variables that OpenAlexSearch reads during initialization
        os.environ["OPENALEX_EMAIL"] = "user@example.com"
        os.environ["OPENALEX_API_KEY"] = "apikey123"

        # Prepare a fake response for requests.get
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"results": []}

        mock_get = MagicMock(return_value=mock_resp)

        try:
            with patch("requests.get", mock_get):
                # Create instance and call search with a large max_results to trigger the min cap
                oa = OpenAlexSearch(query="test query", sort="relevance_score:desc")
                results = oa.search(max_results=100)

            # Expect no results returned because we mocked an empty results list
            self.assertEqual(results, [])

            # Verify requests.get was called once with correct URL and params
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            # First positional arg is the URL
            self.assertEqual(args[0], oa.BASE_URL)

            params = kwargs.get("params", {})
            self.assertEqual(params.get("search"), "test query")
            # per_page should be min(100, 25) == 25
            self.assertEqual(params.get("per_page"), 25)
            self.assertEqual(params.get("sort"), "relevance_score:desc")
            # Environment variables should have been included in params
            self.assertEqual(params.get("mailto"), "user@example.com")
            self.assertEqual(params.get("api_key"), "apikey123")
        finally:
            # Clean up environment
            os.environ.pop("OPENALEX_EMAIL", None)
            os.environ.pop("OPENALEX_API_KEY", None)
