import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.semantic_scholar.semantic_scholar')
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
        """Verify that SemanticScholarSearch.search builds the expected params dict and calls requests.get accordingly."""
        # Patch requests.get to capture the call and return a dummy successful response
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"data": []}
            mock_get.return_value = mock_response

            # Instantiate with a specific query and use a non-default max_results
            s = SemanticScholarSearch(query="deep learning")
            results = s.search(max_results=5)

            # Verify the search returned the empty list from our mocked response
            self.assertEqual(results, [])

            # Ensure requests.get was called exactly once
            mock_get.assert_called_once()

            # Extract the params passed to requests.get (handle positional or keyword usage)
            call_args = mock_get.call_args
            pos_args = call_args[0]
            kw_args = call_args[1]
            if len(pos_args) >= 2:
                passed_params = pos_args[1]
            else:
                passed_params = kw_args.get("params")

            # Expected params constructed exactly as in the target code
            expected_params = {
                "query": s.query,
                "limit": 5,
                "fields": "title,abstract,url,venue,year,authors,isOpenAccess,openAccessPdf",
                "sort": s.sort,
            }

            # Verify URL and params
            # URL should be passed as the first positional argument
            called_url = pos_args[0] if len(pos_args) >= 1 else kw_args.get("url")
            self.assertEqual(called_url, s.BASE_URL)
            self.assertEqual(passed_params, expected_params)
