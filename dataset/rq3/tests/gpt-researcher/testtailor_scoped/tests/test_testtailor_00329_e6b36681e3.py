import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.pubmed_central.pubmed_central')
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
        """Ensure branch where db_type != 'pubmed' uses raw query as search term."""
        # Create searcher and force a non-pubmed DB type to hit the target branch
        searcher = PubMedCentralSearch(query="my test query")
        searcher.db_type = "pmc"  # explicit non-'pubmed' value to exercise search_term = self.query

        # Prepare mock response for requests.get
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"esearchresult": {"idlist": ["PMC123", "PMC456"]}}

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            result_ids = searcher._search_articles(max_results=2)

            # Verify returned IDs match the mocked payload
            self.assertEqual(result_ids, ["PMC123", "PMC456"])

            # Verify the outgoing request used the raw query as the term (no extra filters)
            called_params = mock_get.call_args[1]["params"]
            self.assertEqual(called_params["term"], "my test query")
            self.assertEqual(called_params["db"], "pmc")
            self.assertEqual(called_params["retmax"], 2)
