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
        """Verify GoogleSearch __init__ uses provided headers and falls back to get_api_key/get_cx_key when headers absent."""
        # Case 1: headers include keys -> should use them and NOT call fallback methods
        with patch.object(GoogleSearch, "get_api_key", autospec=True) as mock_get_api, \
             patch.object(GoogleSearch, "get_cx_key", autospec=True) as mock_get_cx:
            gs = GoogleSearch(query="test-query", headers={"google_api_key": "HEADER_API", "google_cx_key": "HEADER_CX"})
            # Basic attribute checks
            self.assertEqual(gs.query, "test-query")
            self.assertEqual(gs.headers["google_api_key"], "HEADER_API")
            # Ensure values came from headers
            self.assertEqual(gs.api_key, "HEADER_API")
            self.assertEqual(gs.cx_key, "HEADER_CX")
            # Ensure fallback methods were not invoked
            mock_get_api.assert_not_called()
            mock_get_cx.assert_not_called()

        # Case 2: headers missing -> should call fallback methods and use their return values
        with patch.object(GoogleSearch, "get_api_key", return_value="ENV_API") as mock_get_api2, \
             patch.object(GoogleSearch, "get_cx_key", return_value="ENV_CX") as mock_get_cx2:
            gs2 = GoogleSearch(query="another-query", headers=None)
            mock_get_api2.assert_called_once()
            mock_get_cx2.assert_called_once()
            self.assertEqual(gs2.api_key, "ENV_API")
            self.assertEqual(gs2.cx_key, "ENV_CX")
