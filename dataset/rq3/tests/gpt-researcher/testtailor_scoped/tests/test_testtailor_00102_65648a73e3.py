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
        """Ensure the search method builds the expected params and calls requests.get."""
        # Patch requests.get so no real HTTP call is made
        with patch('requests.get') as mock_get:
            # Prepare a fake successful response
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {
                "data": [
                    {
                        "title": "Paper 1",
                        "abstract": "Abstract 1",
                        "isOpenAccess": True,
                        "openAccessPdf": {"url": "http://pdf1"},
                    }
                ]
            }
            mock_get.return_value = mock_resp

            # Instantiate with a known query and sort criterion
            searcher = SemanticScholarSearch(query="quantum computing", sort="publicationDate")

            # Call the method under test
            results = searcher.search(max_results=5)

            # Verify results are returned as expected from the mocked response
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Paper 1")
            self.assertEqual(results[0]["href"], "http://pdf1")
            self.assertEqual(results[0]["body"], "Abstract 1")

            # Verify requests.get was called correctly with the BASE_URL and the expected params
            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]
            called_params = mock_get.call_args[1]["params"]

            self.assertEqual(called_url, searcher.BASE_URL)
            expected_params = {
                "query": "quantum computing",
                "limit": 5,
                "fields": "title,abstract,url,venue,year,authors,isOpenAccess,openAccessPdf",
                "sort": searcher.sort,
            }
            self.assertEqual(called_params, expected_params)
