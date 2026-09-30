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
        """Ensure extract_clean_markdown uses dom_service path when browser_session is None."""
        # Prepare a dummy HTML output from the serializer so we can predict stats
        dummy_html = '<p>Test Content</p><a href="http://example.com">a link</a>'

        # Backup original HTMLSerializer and restore later
        original_serializer = extract_clean_markdown.__globals__.get('HTMLSerializer')

        # Create a dummy serializer that returns predictable HTML regardless of node
        class DummySerializer:
            def __init__(self, extract_links: bool = False):
                self.extract_links = extract_links

            def serialize(self, node, depth: int = 0) -> str:
                # Return deterministic HTML for markdownify to process
                return dummy_html

        # Fake DomService with async get_dom_tree method
        class FakeDomService:
            async def get_dom_tree(self, target_id: str, all_frames=None):
                # Return anything as enhanced_dom_tree because DummySerializer ignores it
                return ("FAKE_NODE", {"timing": 0.0})

        # Patch the HTMLSerializer in the target function's globals to our DummySerializer
        extract_clean_markdown.__globals__['HTMLSerializer'] = DummySerializer

        try:
            dom_service = FakeDomService()

            # Use __import__ to avoid relying on an explicit asyncio import in the test file
            asyncio_mod = __import__('asyncio')
            loop = asyncio_mod.get_event_loop()
            content, stats = loop.run_until_complete(
                extract_clean_markdown(browser_session=None, dom_service=dom_service, target_id='t-1', extract_links=True, extract_images=False)
            )

            # Validate branch taken and stats content
            self.assertIsInstance(content, str)
            self.assertIn('Test Content', content)  # markdown should include the text
            self.assertIn('a link', content)  # link text should be present
            self.assertIsInstance(stats, dict)
            self.assertEqual(stats.get('method'), 'dom_service')  # target branch
            # DOM service path should not include URL in stats
            self.assertNotIn('url', stats)
            # original_html_chars should match length of dummy_html returned by DummySerializer
            self.assertEqual(stats.get('original_html_chars'), len(dummy_html))
        finally:
            # Restore original serializer to avoid side effects
            if original_serializer is not None:
                extract_clean_markdown.__globals__['HTMLSerializer'] = original_serializer
            else:
                extract_clean_markdown.__globals__.pop('HTMLSerializer', None)
