import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.web_base_loader.web_base_loader')
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
        """Verify that the constructor assigns link and handles the session argument correctly."""
        # Provided session should be used as-is
        custom_session = requests.Session()
        scraper_with_custom = WebBaseLoaderScraper("http://example.com", session=custom_session)
        self.assertEqual(scraper_with_custom.link, "http://example.com")
        self.assertIs(scraper_with_custom.session, custom_session)

        # None session should result in a new requests.Session being created
        scraper_with_none = WebBaseLoaderScraper("http://example.org", session=None)
        self.assertEqual(scraper_with_none.link, "http://example.org")
        self.assertIsInstance(scraper_with_none.session, requests.Session)
        self.assertIsNot(scraper_with_none.session, custom_session)

        # Falsy but non-None session (e.g., empty string) should also create a new requests.Session
        scraper_with_falsy = WebBaseLoaderScraper("http://example.net", session="")
        self.assertEqual(scraper_with_falsy.link, "http://example.net")
        self.assertIsInstance(scraper_with_falsy.session, requests.Session)
        self.assertIsNot(scraper_with_falsy.session, custom_session)
