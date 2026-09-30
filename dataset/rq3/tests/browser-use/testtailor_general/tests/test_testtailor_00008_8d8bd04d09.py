import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.downloads_watchdog')
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
        """Verify filename is extracted from various Content-Disposition forms."""
        # double-quoted filename
        self.assertEqual(
            _filename_from_content_disposition('attachment; filename="report.pdf"'),
            'report.pdf',
        )
        # single-quoted filename with spaces
        self.assertEqual(
            _filename_from_content_disposition("attachment; filename='weird name.txt'"),
            'weird name.txt',
        )
        # unquoted filename
        self.assertEqual(
            _filename_from_content_disposition('inline; filename=unquoted.txt'),
            'unquoted.txt',
        )
        # filename param absent
        self.assertIsNone(
            _filename_from_content_disposition('inline; name="no_filename"'),
        )
        # quoted filename containing semicolon (should keep semicolon because it's inside quotes)
        self.assertEqual(
            _filename_from_content_disposition('attachment; filename="a;b.txt"; size=123'),
            'a;b.txt',
        )
