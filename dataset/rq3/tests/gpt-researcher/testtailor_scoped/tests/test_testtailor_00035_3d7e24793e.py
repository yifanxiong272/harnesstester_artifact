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
        """Ensure base URLs are set and api_key is read from environment (None when missing)."""
        # Remove any existing NCBI_API_KEY for this test and restore afterwards
        prev_key = os.environ.pop('NCBI_API_KEY', None)
        try:
            # Instantiate the class which will read the environment variable
            searcher = PubMedCentralSearch(query="test query")

            # Verify base URLs are set correctly
            self.assertEqual(
                searcher.base_search_url,
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            )
            self.assertEqual(
                searcher.base_fetch_url,
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            )

            # Verify api_key is None when not set in environment
            self.assertIsNone(searcher.api_key)
        finally:
            # Restore previous environment state
            if prev_key is not None:
                os.environ['NCBI_API_KEY'] = prev_key
