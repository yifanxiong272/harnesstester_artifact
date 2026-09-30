import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.browser')
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
        """complete the test case here"""
        # Prepare inputs
        urls = ["http://example.com/a", "http://example.com/b"]

        # Minimal researcher mock with required attributes and methods
        class DummyCfg:
            max_scraper_workers = 1
            scraper_rate_limit_delay = 0

        class DummyResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = "ws-connection"
                self.cfg = DummyCfg()
                self._sources = None
                self._images = None

            def add_research_sources(self, sources):
                self._sources = sources

            def add_research_images(self, images):
                self._images = images

            def get_research_images(self):
                return []  # start with no existing images

        researcher = DummyResearcher()

        # Instantiate BrowserManager (uses researcher.cfg in __init__)
        bm = BrowserManager(researcher)

        # Prepare fake async functions to capture calls and control behavior
        fake_stream_calls = []

        async def fake_stream_output(*args, **kwargs):
            # record call for assertions
            fake_stream_calls.append((args, kwargs))
            return None

        async def fake_scrape_urls(url_list, cfg, worker_pool):
            # return a small scraped_content list and some images
            scraped_content = [{"url": u, "text": f"content for {u}"} for u in url_list]
            images = [
                {"url": "http://img/1.png", "score": 0.9},
                {"url": "http://img/2.png", "score": 0.8},
            ]
            return scraped_content, images

        def fake_get_image_hash(url):
            return f"hash-{url}"

        # Patch the globals used by BrowserManager.browse_urls
        globals_dict = BrowserManager.browse_urls.__globals__
        # Save originals to restore later
        orig_stream = globals_dict.get("stream_output")
        orig_scrape = globals_dict.get("scrape_urls")
        orig_get_hash = globals_dict.get("get_image_hash")

        globals_dict["stream_output"] = fake_stream_output
        globals_dict["scrape_urls"] = fake_scrape_urls
        globals_dict["get_image_hash"] = fake_get_image_hash

        try:
            # Run the async method using __import__ to avoid adding an import statement
            asyncio = __import__("asyncio")
            result = asyncio.run(bm.browse_urls(urls))

            # Verify the function returned the scraped content
            self.assertEqual(len(result), len(urls))
            self.assertEqual(result[0]["url"], urls[0])

            # Verify stream_output was called and the first call is the "scraping_urls" log
            self.assertGreaterEqual(len(fake_stream_calls), 1)
            first_call_args, first_call_kwargs = fake_stream_calls[0]
            # args structure: ("logs", "scraping_urls", message, websocket, ...)
            self.assertEqual(first_call_args[0], "logs")
            self.assertEqual(first_call_args[1], "scraping_urls")
            # message should mention the number of URLs
            self.assertIn("Scraping content from 2 URLs", first_call_args[2])
            # websocket passed through
            self.assertEqual(first_call_args[3], researcher.websocket)

        finally:
            # Restore originals
            if orig_stream is not None:
                globals_dict["stream_output"] = orig_stream
            else:
                globals_dict.pop("stream_output", None)

            if orig_scrape is not None:
                globals_dict["scrape_urls"] = orig_scrape
            else:
                globals_dict.pop("scrape_urls", None)

            if orig_get_hash is not None:
                globals_dict["get_image_hash"] = orig_get_hash
            else:
                globals_dict.pop("get_image_hash", None)
