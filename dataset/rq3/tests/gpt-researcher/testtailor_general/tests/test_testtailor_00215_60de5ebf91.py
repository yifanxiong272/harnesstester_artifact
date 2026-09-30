import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.scraper')
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
        """Ensure _check_pkg is called when scraper == 'firecrawl' and duplicates are removed."""
        mock_worker_pool = unittest.mock.Mock()
        urls = ["http://example.com", "http://example.com"]
        with unittest.mock.patch.object(Scraper, "_check_pkg") as mock_check:
            s = Scraper(urls=urls, user_agent="test-agent", scraper="firecrawl", worker_pool=mock_worker_pool)
            mock_check.assert_called_once_with("firecrawl")
            # verify deduplication occurred and attributes set
            self.assertEqual(s.scraper, "firecrawl")
            self.assertEqual(s.urls, ["http://example.com"])
