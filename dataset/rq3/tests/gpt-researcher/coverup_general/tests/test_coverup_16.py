# file: gpt_researcher/scraper/scraper.py:108-169
# asked: {"lines": [112, 113, 114, 115, 118, 119, 122, 123, 125, 126, 127, 128, 129, 130, 133, 134, 135, 136, 137, 138, 139, 143, 144, 145, 147, 148, 149, 151, 152, 153, 154, 155, 156, 157, 160, 161, 162, 163, 164, 167, 168, 169], "branches": [[122, 123], [122, 125], [133, 134], [133, 143], [151, 152], [151, 160]]}
# gained: {"lines": [112, 113, 114, 115, 118, 119, 122, 123, 125, 126, 127, 128, 129, 130, 133, 134, 135, 136, 137, 138, 139, 143, 144, 145, 147, 148, 149, 151, 160, 161, 162, 163, 164, 167, 168, 169], "branches": [[122, 123], [122, 125], [133, 134], [133, 143], [151, 160]]}

import asyncio
import types
import pytest
from unittest.mock import MagicMock

from gpt_researcher.scraper.scraper import Scraper


class DummyWorkerPool:
    def __init__(self, executor=None):
        self.executor = executor

    def throttle(self):
        # async context manager
        @pytest.mark.asyncio
        async def _cm():
            try:
                yield
            finally:
                return
        # Can't return a pytest-marked coroutine; instead use a real async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _async_cm():
            yield

        return _async_cm()


@pytest.mark.asyncio
async def test_extract_data_async_short_content(monkeypatch):
    worker_pool = DummyWorkerPool()
    sc = Scraper(urls=["http://example.com"], user_agent="ua", scraper="none", worker_pool=worker_pool)

    # Prepare an async scraper class whose scrape_async returns short content
    class AsyncScraper:
        def __init__(self, link, session):
            self.link = link
            self.session = session

        async def scrape_async(self):
            return ("short", [], "short title")

    # Monkeypatch get_scraper to return our class
    monkeypatch.setattr(sc, "get_scraper", lambda link: AsyncScraper)

    # Replace logger with MagicMock to capture warnings
    mock_logger = MagicMock()
    sc.logger = mock_logger

    result = await sc.extract_data_from_url("http://example.com", session=None)

    # Verify returned dict matches the short-content branch
    assert result == {
        "url": "http://example.com",
        "raw_content": None,
        "image_urls": [],
        "title": "short title",
    }

    # Ensure a warning about short content was logged
    assert mock_logger.warning.called
    # The warning message should mention the URL
    warning_msgs = [args[0] for args, _ in mock_logger.warning.call_args_list]
    assert any("Content too short" in m and "http://example.com" in m for m in warning_msgs)


@pytest.mark.asyncio
async def test_extract_data_sync_long_content(monkeypatch):
    # Create a dummy executor (not used because we'll monkeypatch run_in_executor)
    worker_pool = DummyWorkerPool(executor=object())
    sc = Scraper(urls=["http://long.com"], user_agent="ua", scraper="none", worker_pool=worker_pool)

    # Prepare a sync scraper class whose scrape returns long content
    long_content = "x" * 200
    class SyncScraper:
        def __init__(self, link, session):
            self.link = link
            self.session = session

        def scrape(self):
            return (long_content, ["img1", "img2"], "long title")

    monkeypatch.setattr(sc, "get_scraper", lambda link: SyncScraper)

    # Replace logger with MagicMock to capture info logs
    mock_logger = MagicMock()
    sc.logger = mock_logger

    # Monkeypatch asyncio.get_running_loop().run_in_executor to synchronously call the function
    class DummyLoop:
        async def run_in_executor(self, executor, func, *args):
            return func(*args)

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: DummyLoop())

    result = await sc.extract_data_from_url("http://long.com", session=None)

    # Verify result contains the long content and images
    assert result["url"] == "http://long.com"
    assert result["raw_content"] == long_content
    assert result["image_urls"] == ["img1", "img2"]
    assert result["title"] == "long title"

    # Ensure info logs about title, content length, and images were emitted
    info_msgs = [args[0] for args, _ in mock_logger.info.call_args_list]
    assert any("Using" in m or "=== Using" in m or "Using" in m for m in info_msgs)
    assert any("Title: long title" in m or "Title: " in m for m in info_msgs)
    assert any("Content length" in m for m in info_msgs)
    assert any("Number of images" in m or "Number of images:" in m for m in info_msgs)


@pytest.mark.asyncio
async def test_extract_data_exception_path(monkeypatch):
    worker_pool = DummyWorkerPool()
    sc = Scraper(urls=["http://err.com"], user_agent="ua", scraper="none", worker_pool=worker_pool)

    # Make get_scraper raise to trigger the exception branch
    def bad_get_scraper(link):
        raise RuntimeError("boom")

    monkeypatch.setattr(sc, "get_scraper", bad_get_scraper)

    mock_logger = MagicMock()
    sc.logger = mock_logger

    result = await sc.extract_data_from_url("http://err.com", session=None)

    # Verify the exception path returns the expected empty result
    assert result == {"url": "http://err.com", "raw_content": None, "image_urls": [], "title": ""}

    # Ensure logger.error was called and includes the URL or exception message
    assert mock_logger.error.called
    err_msgs = [args[0] for args, _ in mock_logger.error.call_args_list]
    assert any("Error processing" in m and "http://err.com" in m for m in err_msgs)
