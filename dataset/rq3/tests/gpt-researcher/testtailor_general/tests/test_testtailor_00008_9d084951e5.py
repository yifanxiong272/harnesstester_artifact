import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.browser.nodriver_scraper')
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
        """Verify domain extraction handles subdomains, ports and IPs as implemented."""
        # subdomain with multi-part TLD -> should return last two labels
        url1 = "https://a.b.example.co.uk/path"
        self.assertEqual(NoDriverScraper.get_domain(url1), "co.uk")

        # regular domain with port -> port remains attached to last label
        url2 = "http://example.com:8080/foo"
        self.assertEqual(NoDriverScraper.get_domain(url2), "example.com:8080")

        # IPv4 with port -> function splits on dots, so returns last two dot-parts (per implementation)
        url3 = "http://127.0.0.1:5000/"
        self.assertEqual(NoDriverScraper.get_domain(url3), "0.1:5000")

        # simple domain without subdomain
        url4 = "https://example.com"
        self.assertEqual(NoDriverScraper.get_domain(url4), "example.com")

        # localhost with port should preserve port
        url5 = "http://localhost:8000/home"
        self.assertEqual(NoDriverScraper.get_domain(url5), "localhost:8000")
