import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.web_base_loader.web_base_loader')
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
        # Arrange
        link = "http://example.com/page"

        # Prepare fake documents the loader should return
        class Doc:
            def __init__(self, page_content):
                self.page_content = page_content

        docs = [Doc("Part1 "), Doc("Part2")]

        # Get the module where WebBaseLoaderScraper is defined so we can patch helpers there
        module = __import__(WebBaseLoaderScraper.__module__, fromlist=['*'])

        # Dummy session to avoid real network calls
        class DummyResponse:
            def __init__(self, content):
                self.content = content

        class DummySession:
            def get(self, url):
                return DummyResponse(b"<html><body></body></html>")

        # Patch the external dependencies used inside scrape()
        with patch('langchain_community.document_loaders.WebBaseLoader') as MockLoader, \
             patch.object(module, 'get_relevant_images', return_value=['http://img/1.png']) as mock_get_images, \
             patch.object(module, 'extract_title', return_value='Page Title') as mock_extract_title:

            # Configure the mocked loader instance
            loader_instance = MockLoader.return_value
            loader_instance.load.return_value = docs

            # Act
            scraper = WebBaseLoaderScraper(link, session=DummySession())
            content, image_urls, title = scraper.scrape()

            # Assert returned values are composed from our mocks
            self.assertEqual(content, "Part1 Part2")
            self.assertEqual(image_urls, ['http://img/1.png'])
            self.assertEqual(title, 'Page Title')

            # Ensure the loader was constructed with the expected link and its requests_kwargs was set
            MockLoader.assert_called_with(link)
            self.assertEqual(getattr(loader_instance, "requests_kwargs", None), {"verify": False})
