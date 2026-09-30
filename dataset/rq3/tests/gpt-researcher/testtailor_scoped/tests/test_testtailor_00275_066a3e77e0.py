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
        """Verify that when db_type is 'pubmed' the search term includes full-text filters."""
        query = "cancer therapy"
        # Instantiate and force db_type to 'pubmed' to hit the branch
        searcher = PubMedCentralSearch(query)
        searcher.db_type = 'pubmed'

        with patch('requests.get') as mock_get:
            # Prepare a fake successful response
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'esearchresult': {'idlist': ['111', '222']}}
            mock_get.return_value = mock_response

            result_ids = searcher._search_articles(max_results=5)

            # Ensure the call returned the mocked id list
            self.assertEqual(result_ids, ['111', '222'])

            # Ensure requests.get was called once and capture the params passed
            mock_get.assert_called_once()
            _, kwargs = mock_get.call_args
            self.assertIn('params', kwargs)
            params = kwargs['params']

            # Expected search term when db_type == 'pubmed'
            expected_term = f"{query} AND (ffrft[filter] OR pmc[filter])"
            self.assertEqual(params.get('term'), expected_term)
            self.assertEqual(params.get('db'), 'pubmed')
            self.assertEqual(params.get('retmax'), 5)
            # api_key may be None but key should exist in params
            self.assertIn('api_key', params)
