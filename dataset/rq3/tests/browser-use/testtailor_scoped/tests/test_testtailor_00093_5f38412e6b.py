import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.markdown_extractor')
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
        """Ensure extract_clean_markdown uses the browser_session path and returns expected stats."""
        # Create a minimal dummy browser session with a populated DOMWatchdog and async URL getter
        class DummyDomWatchdog:
            def __init__(self):
                # The actual serializer is patched below, so this can be any object
                self.enhanced_dom_tree = object()

        class DummyBrowserSession:
            def __init__(self):
                self._dom_watchdog = DummyDomWatchdog()

            async def get_current_page_url(self):
                return "https://example.test/page"

        browser_session = DummyBrowserSession()

        # Provide a simple HTML payload that the serializer would return
        fake_html = "<p>Hello <a href='https://example.com'>link</a> <img src='https://img.jpg' alt='i' /></p>"

        # Patch the HTMLSerializer.serialize method so we don't need to construct a full enhanced DOM node
        with unittest.mock.patch(
            "browser_use.dom.serializer.html_serializer.HTMLSerializer.serialize", return_value=fake_html
        ):
            # Run the async function using __import__ to avoid relying on a top-level asyncio name
            asyncio_mod = __import__('asyncio')
            loop = asyncio_mod.new_event_loop()
            try:
                asyncio_mod.set_event_loop(loop)
                content, stats = loop.run_until_complete(
                    extract_clean_markdown(browser_session=browser_session, extract_links=True, extract_images=True)
                )
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        # Validate outputs
        self.assertIsInstance(content, str)
        self.assertIn("Hello", content)
        self.assertIn("link", content)
        self.assertEqual(stats.get("method"), "enhanced_dom_tree")
        self.assertEqual(stats.get("url"), "https://example.test/page")
        # Basic sanity checks for statistics keys added by the function
        self.assertIn("original_html_chars", stats)
        self.assertIn("initial_markdown_chars", stats)
        self.assertIn("final_filtered_chars", stats)
