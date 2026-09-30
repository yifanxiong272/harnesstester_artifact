import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.init_cmd')
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
        """Ensure _fetch_template_list requests the correct URL and parses JSON."""
        # prepare a fake response that works as a context manager and returns JSON bytes
        fake_response = MagicMock()
        fake_response.read.return_value = b'{"ok": true, "items": [1,2,3]}'
        fake_ctx = MagicMock()
        fake_ctx.__enter__.return_value = fake_response
        fake_ctx.__exit__.return_value = None

        expected_url = f'{TEMPLATE_REPO_URL}/templates.json'

        with patch('urllib.request.urlopen', return_value=fake_ctx) as mock_urlopen:
            result = _fetch_template_list()

        mock_urlopen.assert_called_once_with(expected_url, timeout=5)
        self.assertEqual(result, {"ok": True, "items": [1, 2, 3]})
