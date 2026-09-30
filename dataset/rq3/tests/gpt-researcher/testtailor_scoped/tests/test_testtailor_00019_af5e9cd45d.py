import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.google.google')
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
        """Test GoogleSearch __init__ uses headers when provided and falls back to getters when not."""
        headers = {'google_api_key': 'API123', 'google_cx_key': 'CX456'}

        # When headers include keys, get_api_key/get_cx_key should not be called
        with patch.object(GoogleSearch, 'get_api_key') as mock_get_api, \
             patch.object(GoogleSearch, 'get_cx_key') as mock_get_cx:
            gs = GoogleSearch(query='my query', headers=headers, query_domains=['ex.com'])
            self.assertEqual(gs.query, 'my query')
            self.assertEqual(gs.headers, headers)
            self.assertEqual(gs.query_domains, ['ex.com'])
            self.assertEqual(gs.api_key, 'API123')
            self.assertEqual(gs.cx_key, 'CX456')
            mock_get_api.assert_not_called()
            mock_get_cx.assert_not_called()

        # When headers not provided, fallback to get_api_key/get_cx_key should be used
        with patch.object(GoogleSearch, 'get_api_key', return_value='ENV_API') as mock_get_api2, \
             patch.object(GoogleSearch, 'get_cx_key', return_value='ENV_CX') as mock_get_cx2:
            gs2 = GoogleSearch(query='q2')
            self.assertEqual(gs2.query, 'q2')
            self.assertEqual(gs2.headers, {})  # headers default to {}
            self.assertIsNone(gs2.query_domains)
            self.assertEqual(gs2.api_key, 'ENV_API')
            self.assertEqual(gs2.cx_key, 'ENV_CX')
            mock_get_api2.assert_called_once()
            mock_get_cx2.assert_called_once()
