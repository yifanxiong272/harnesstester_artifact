import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searx.searx')
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
        """Test SearxSearch __init__ sets query, handles query_domains falsy/truthy and normalizes SEARX_URL."""
        # Preserve existing env var
        prev = os.environ.get('SEARX_URL')
        try:
            # Case 1: SEARX_URL without trailing slash, query_domains falsy (empty list -> becomes None)
            os.environ['SEARX_URL'] = 'https://example.com'
            s = SearxSearch(query='my query', query_domains=[])
            self.assertEqual(s.query, 'my query')
            self.assertIsNone(s.query_domains)
            self.assertEqual(s.base_url, 'https://example.com/')

            # Case 2: query_domains provided (non-empty list) should be preserved as-is
            domains = ['example.org']
            s2 = SearxSearch(query='q2', query_domains=domains)
            self.assertEqual(s2.query, 'q2')
            self.assertIs(s2.query_domains, domains)

            # Case 3: SEARX_URL already has trailing slash (should remain unchanged)
            os.environ['SEARX_URL'] = 'https://example.org/'
            s3 = SearxSearch(query='q3')
            self.assertEqual(s3.base_url, 'https://example.org/')

        finally:
            # Restore environment
            if prev is None:
                os.environ.pop('SEARX_URL', None)
            else:
                os.environ['SEARX_URL'] = prev
