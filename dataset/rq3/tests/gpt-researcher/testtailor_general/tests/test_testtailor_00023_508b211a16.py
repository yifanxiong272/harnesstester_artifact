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
        """Test that Scraper deduplicates URLs, preserves order, sets session UA and stores scraper/worker_pool"""
        urls = [
            "http://example.com/page1",
            "http://example.com/page2",
            "http://example.com/page1",  # duplicate, should be removed
        ]
        user_agent = "test-agent/1.0"
        # Create a WorkerPool; it's lightweight to construct for this test
        worker_pool = WorkerPool(max_workers=2, rate_limit_delay=0.0)

        s = Scraper(urls, user_agent, "bs", worker_pool)

        # Duplicates removed and order preserved
        expected_unique = ["http://example.com/page1", "http://example.com/page2"]
        self.assertEqual(s.urls, expected_unique)
        self.assertEqual(len(s.urls), 2)

        # Session correctly created and User-Agent header set
        self.assertIsInstance(s.session, requests.Session)
        self.assertEqual(s.session.headers.get("User-Agent"), user_agent)

        # Scraper selection and worker pool stored
        self.assertEqual(s.scraper, "bs")
        self.assertIs(s.worker_pool, worker_pool)
