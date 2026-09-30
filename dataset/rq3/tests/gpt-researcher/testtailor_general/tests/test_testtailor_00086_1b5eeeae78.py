import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.beautiful_soup.beautiful_soup')
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
        """Verify that the constructor assigns link and session correctly, including default None."""
        link = "http://example.com/test-page"
        mock_session = object()

        scraper = BeautifulSoupScraper(link, session=mock_session)
        self.assertEqual(scraper.link, link)
        self.assertIs(scraper.session, mock_session)

        # also verify default session is None when not provided
        scraper_default = BeautifulSoupScraper(link)
        self.assertEqual(scraper_default.link, link)
        self.assertIsNone(scraper_default.session)
