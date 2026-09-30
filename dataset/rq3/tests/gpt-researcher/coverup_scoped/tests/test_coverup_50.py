# file: gpt_researcher/skills/researcher.py:926-961
# asked: {"lines": [936, 939, 940, 941, 942, 945, 946, 949, 952, 953, 956, 959, 961], "branches": [[940, 941], [940, 945], [941, 940], [941, 942], [945, 946], [945, 949], [952, 953], [952, 956]]}
# gained: {"lines": [936, 939, 940, 941, 942, 945, 946, 949, 952, 953, 956, 959, 961], "branches": [[940, 941], [940, 945], [941, 940], [941, 942], [945, 946], [945, 949], [952, 953], [952, 956]]}

import pytest
import asyncio
from unittest.mock import Mock

from gpt_researcher.skills.researcher import ResearchConductor

class DummyScraperManager:
    def __init__(self, func):
        # func should be an async callable
        self._func = func

    async def browse_urls(self, urls):
        return await self._func(urls)

class DummyResearcher:
    def __init__(self):
        self.visited_urls = set()
        self.scraper_manager = None

@pytest.mark.asyncio
async def test_extract_content_no_urls(monkeypatch):
    """
    If search results contain no dicts with 'href', _extract_content should:
    - log the count
    - return an empty list
    """
    researcher = DummyResearcher()
    conductor = ResearchConductor(researcher)

    # Replace logger with a mock to capture .info calls
    mock_logger = Mock()
    conductor.logger = mock_logger

    results = ["not a dict", {"nohref": "1"}, 123]
    out = await conductor._extract_content(results)

    assert out == []  # should return empty list when no urls found
    mock_logger.info.assert_called_once_with(f"Extracting content from {len(results)} search results")

@pytest.mark.asyncio
async def test_extract_content_all_urls_already_visited(monkeypatch):
    """
    If all URLs have already been visited, _extract_content should:
    - log the count
    - return an empty list
    - not call scraper_manager.browse_urls
    """
    researcher = DummyResearcher()
    # mark the URLs as already visited
    researcher.visited_urls.update({"http://a.com", "http://b.com"})

    # Create a scraper_manager whose browse_urls would raise if called
    async def bad_browse(urls):
        raise AssertionError("browse_urls should not be called when all URLs are visited")
    researcher.scraper_manager = DummyScraperManager(bad_browse)

    conductor = ResearchConductor(researcher)
    mock_logger = Mock()
    conductor.logger = mock_logger

    results = [{"href": "http://a.com"}, {"href": "http://b.com"}]
    out = await conductor._extract_content(results)

    assert out == []  # no new URLs to scrape
    mock_logger.info.assert_called_once_with(f"Extracting content from {len(results)} search results")

@pytest.mark.asyncio
async def test_extract_content_new_urls_scraped_and_visited_updated(monkeypatch):
    """
    When there are new URLs, _extract_content should:
    - call scrape on the new URLs
    - update researcher.visited_urls with the new URLs
    - return the scraped content
    """
    researcher = DummyResearcher()

    scraped = ["page1 content", "page2 content"]
    captured_urls = []

    async def good_browse(urls):
        # capture and return a predictable result
        captured_urls.extend(urls)
        return scraped

    researcher.scraper_manager = DummyScraperManager(good_browse)

    conductor = ResearchConductor(researcher)
    mock_logger = Mock()
    conductor.logger = mock_logger

    results = [
        {"href": "http://new1.com"},
        {"href": "http://new2.com"},
        {"other": "ignore_me"}
    ]

    out = await conductor._extract_content(results)

    # returned content should match what the scraper returned
    assert out == scraped

    # visited_urls should be updated with the two new URLs
    assert "http://new1.com" in researcher.visited_urls
    assert "http://new2.com" in researcher.visited_urls

    # ensure the scraper was called with the expected new URLs
    assert set(captured_urls) == {"http://new1.com", "http://new2.com"}

    # logging called with the correct count
    mock_logger.info.assert_called_once_with(f"Extracting content from {len(results)} search results")
