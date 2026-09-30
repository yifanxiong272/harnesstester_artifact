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
        class Page:
            def __init__(self, content, source):
                self.page_content = content
                self.metadata = {"source": source}

        loader = OnlineDocumentLoader(urls=["http://example.com/doc.pdf"])

        async def fake_download_and_process(url):
            # return one page with content to trigger the docs.append branch
            return [Page("Hello world", url)]

        # replace the real network/IO method with our fake coroutine
        loader._download_and_process = fake_download_and_process

        # import asyncio at runtime to avoid top-level import statement
        asyncio = __import__('asyncio')
        result = asyncio.get_event_loop().run_until_complete(loader.load())

        self.assertEqual(
            result,
            [{"raw_content": "Hello world", "url": "http://example.com/doc.pdf"}]
        )
