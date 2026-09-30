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
        """Test extract_clean_markdown takes the browser_session path and returns content + stats."""
        # Get reference to the module where extract_clean_markdown is defined
        mod = __import__(extract_clean_markdown.__module__, fromlist=['HTMLSerializer'])

        # Monkeypatch HTMLSerializer in the module to a simple serializer that returns the provided enhanced_dom_tree text
        class DummyHTMLSerializer:
            def __init__(self, extract_links: bool = False):
                self.extract_links = extract_links

            def serialize(self, node, depth: int = 0) -> str:
                # If node is a simple string, return it directly; otherwise attempt to read a `text` attribute
                if isinstance(node, str):
                    return node
                # fallback: try common attribute names
                return getattr(node, 'text', '') or getattr(node, 'node_value', '') or ''

        # Patch the module's HTMLSerializer
        mod.HTMLSerializer = DummyHTMLSerializer

        # Ensure the markdownify import inside the function resolves: inject a dummy 'markdownify' module
        sys = __import__('sys')
        types = __import__('types')
        md_module = types.ModuleType('markdownify')

        # Provide a markdownify.markdownify function that returns the input HTML unchanged (accepts kwargs)
        def fake_markdownify(html, **kwargs):
            return html

        md_module.markdownify = fake_markdownify
        # Insert into sys.modules so the in-function import finds it
        sys.modules['markdownify'] = md_module

        # Create a fake DOMWatchdog with cached enhanced_dom_tree (simple string content)
        class DummyDOMWatchdog:
            def __init__(self, tree):
                self.enhanced_dom_tree = tree

        # Create a fake browser session with required attributes and coroutine method
        class DummyBrowserSession:
            def __init__(self, dom_watchdog, url="http://example.com"):
                self._dom_watchdog = dom_watchdog
                self._url = url

            async def get_current_page_url(self):
                return self._url

        # Provide simple HTML content that includes characters requiring escaping and normal text
        enhanced_tree_content = "Hello <world>"

        browser_session = DummyBrowserSession(DummyDOMWatchdog(enhanced_tree_content))

        # Run the async function
        asyncio = __import__('asyncio')
        result_content, stats = asyncio.run(
            extract_clean_markdown(browser_session=browser_session, extract_links=False, extract_images=False)
        )

        # Basic assertions to validate the branch behaviour and outputs
        self.assertIsInstance(result_content, str)
        self.assertIn("Hello", result_content)  # content should include the text node content
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats.get("method"), "enhanced_dom_tree")
        self.assertEqual(stats.get("url"), "http://example.com")
        self.assertGreater(stats.get("original_html_chars", 0), 0)
        self.assertGreater(stats.get("final_filtered_chars", 0), 0)
