import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.arxiv.arxiv')
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
        """Verify ArxivScraper stores link and session correctly on initialization."""
        # explicit session provided
        link = "http://arxiv.org/abs/1234.5678"
        session = object()
        scraper = ArxivScraper(link, session=session)
        self.assertEqual(scraper.link, link)
        self.assertIs(scraper.session, session)

        # default session (should be None)
        link2 = "http://arxiv.org/abs/9876.5432"
        scraper2 = ArxivScraper(link2)
        self.assertEqual(scraper2.link, link2)
        self.assertIsNone(scraper2.session)
