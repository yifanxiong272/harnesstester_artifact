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
        """Ensure that when OPENALEX_EMAIL is set, the search adds mailto to the params."""
        # Arrange: set environment variable and create a searcher
        os.environ["OPENALEX_EMAIL"] = "tester@example.com"
        try:
            searcher = OpenAlexSearch(query="quantum entanglement")

            # Prepare a fake successful response from requests.get
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"results": []}

            # Act: patch requests.get and call search
            with patch("requests.get", return_value=mock_resp) as mock_get:
                results = searcher.search(max_results=5)

            # Assert: search returned an empty list (from our fake response)
            self.assertEqual(results, [])

            # Assert: requests.get was called and mailto param was included
            mock_get.assert_called_once()
            called_args, called_kwargs = mock_get.call_args
            # URL should be the BASE_URL
            self.assertEqual(called_args[0], OpenAlexSearch.BASE_URL)
            params = called_kwargs.get("params", {})
            self.assertIn("mailto", params)
            self.assertEqual(params["mailto"], "tester@example.com")
            # Also check other expected params
            self.assertEqual(params["search"], "quantum entanglement")
            self.assertEqual(params["per_page"], 5)
            self.assertEqual(params["sort"], searcher.sort)
        finally:
            # Clean up environment variable
            os.environ.pop("OPENALEX_EMAIL", None)
