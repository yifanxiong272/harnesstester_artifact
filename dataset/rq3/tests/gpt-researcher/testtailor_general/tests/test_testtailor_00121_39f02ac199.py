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
        """Ensure _check_pkg is called when scraper == 'tavily_extract' and URLs are deduplicated."""
        urls = ["http://example.com/page1", "http://example.com/page2", "http://example.com/page1"]
        dummy_worker = object()

        # Patch the _check_pkg method so we don't attempt any real package checks/installations.
        with patch.object(Scraper, "_check_pkg") as mock_check_pkg:
            scraper_instance = Scraper(urls=urls, user_agent="test-agent", scraper="tavily_extract", worker_pool=dummy_worker)

            # _check_pkg should have been invoked exactly once with the scrapper name
            mock_check_pkg.assert_called_once_with("tavily_extract")

            # Verify deduplication preserved order and removed the duplicate
            self.assertEqual(scraper_instance.urls, ["http://example.com/page1", "http://example.com/page2"])
            # Verify scraper attribute set correctly
            self.assertEqual(scraper_instance.scraper, "tavily_extract")
