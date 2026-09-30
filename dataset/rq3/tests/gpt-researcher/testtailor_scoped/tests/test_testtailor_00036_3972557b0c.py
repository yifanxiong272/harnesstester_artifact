import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.document.online_document')
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
        """Ensure OnlineDocumentLoader stores provided urls argument on initialization."""
        urls = ['http://example.com/doc.pdf', 'https://example.org/readme.md']
        loader = OnlineDocumentLoader(urls)
        # The constructor should assign the same object reference
        self.assertIs(loader.urls, urls)
        # And the value should match the input list
        self.assertEqual(loader.urls, urls)
