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
        """Verify PubMedCentralSearch __init__ sets base URLs and reads NCBI_API_KEY from environment,
        and that a missing API key triggers the expected warning and default behavior.
        """
        # Case 1: NCBI_API_KEY is set
        with patch.dict(os.environ, {
            'NCBI_API_KEY': 'TESTKEY123',
            'PUBMED_DB': 'pubmed',
            'PUBMED_ARG_CUSTOM': 'custom_value'
        }, clear=False):
            searcher = PubMedCentralSearch(query="sars-cov-2")
            # Base URLs should be set correctly
            self.assertEqual(searcher.base_search_url, "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi")
            self.assertEqual(searcher.base_fetch_url, "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi")
            # API key should be read from environment
            self.assertEqual(searcher.api_key, "TESTKEY123")
            # db_type should reflect PUBMED_DB
            self.assertEqual(searcher.db_type, "pubmed")
            # Params should include the custom env var (lowercased key) and defaults
            self.assertIn('custom', searcher.params)
            self.assertEqual(searcher.params['custom'], 'custom_value')
            self.assertEqual(searcher.params.get('sort'), 'relevance')
            self.assertEqual(searcher.params.get('retmode'), 'json')

        # Case 2: NCBI_API_KEY is not set -> warning printed and api_key is None, db_type defaults to 'pmc'
        with patch.dict(os.environ, {}, clear=True):
            with patch('builtins.print') as mock_print:
                searcher_no_key = PubMedCentralSearch(query="influenza")
            # print should have been called with the warning message
            mock_print.assert_called_with("Warning: NCBI_API_KEY not set. Requests will be rate-limited.")
            self.assertIsNone(searcher_no_key.api_key)
            # db_type should default to pmc
            self.assertEqual(searcher_no_key.db_type, 'pmc')
            # Params default values still present
            self.assertEqual(searcher_no_key.params.get('sort'), 'relevance')
            self.assertEqual(searcher_no_key.params.get('retmode'), 'json')
