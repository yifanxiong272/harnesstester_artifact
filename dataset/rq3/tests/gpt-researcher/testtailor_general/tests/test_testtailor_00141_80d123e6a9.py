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
        """Ensure search builds params with search, per_page capped at 25, and sort, and passes them to requests.get."""
        query = "quantum entanglement"
        # Instantiate with default sort
        searcher = OpenAlexSearch(query=query)

        # Prepare a fake successful response with empty results
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}

        expected_params = {
            "search": query,
            "per_page": 25,  # cap applied since we will request more than 25
            "sort": searcher.sort,
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            results = searcher.search(max_results=100)  # request >25 to exercise min(...,25)
            # Function should return empty list because json results are empty
            self.assertEqual(results, [])
            # requests.get must be called exactly once with the BASE_URL, expected params, and timeout=10
            mock_get.assert_called_once_with(searcher.BASE_URL, params=expected_params, timeout=10)
