import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.document.online_document')
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
        """When downloaded pages have empty page_content, load should raise ValueError."""
        # ensure asyncio is available without using an import statement
        asyncio = __import__("asyncio")

        # create a loader with one url
        loader = OnlineDocumentLoader(urls=["http://example.com/empty"])

        # dummy page object with empty content
        class DummyPage:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata

        # replace _download_and_process with an async function that returns a page with empty content
        async def dummy_download_and_process(url):
            return [DummyPage(page_content="", metadata={"source": url})]

        loader._download_and_process = dummy_download_and_process

        # run the async load and expect ValueError because no docs will be collected
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            with self.assertRaises(ValueError):
                loop.run_until_complete(loader.load())
        finally:
            try:
                loop.close()
            except Exception:
                pass
