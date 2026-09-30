# file: gpt_researcher/skills/browser.py:37-84
# asked: {"lines": [47, 48, 49, 50, 51, 52, 55, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 84], "branches": [[47, 48], [47, 55], [62, 63], [62, 84]]}
# gained: {"lines": [47, 48, 49, 50, 51, 52, 55, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 74, 75, 77, 78, 79, 80, 81, 84], "branches": [[47, 48], [47, 55], [62, 63], [62, 84]]}

import importlib
import types
import pytest

def import_browser_module():
    candidates = [
        "gpt_researcher.gpt_researcher.skills.browser",
        "gpt_researcher.skills.browser",
        "gpt_researcher.gpt_researcher.skills.browser",
        "gpt_researcher.browser",
    ]
    last_err = None
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_err = e
    raise last_err

@pytest.mark.asyncio
async def test_browse_urls_verbose_true_calls_stream_and_adds_sources_and_images(monkeypatch):
    browser_mod = import_browser_module()
    BrowserManager = getattr(browser_mod, "BrowserManager")

    # Capture stream_output calls
    stream_calls = []
    async def mock_stream_output(*args, **kwargs):
        stream_calls.append({"args": args, "kwargs": kwargs})

    # Mock scrape_urls to return content and images
    scraped_content = [{"url": "http://a", "text": "A"}, {"url": "http://b", "text": "B"}]
    images = ["i1", "i2", "i3", "i4", "i5"]
    async def mock_scrape_urls(urls, cfg, worker_pool):
        assert isinstance(urls, list)
        # cfg passed through but not used
        return scraped_content, images

    monkeypatch.setattr(browser_mod, "stream_output", mock_stream_output, raising=False)
    monkeypatch.setattr(browser_mod, "scrape_urls", mock_scrape_urls, raising=False)

    # Fake researcher with proper cfg attributes used by BrowserManager.__init__
    added_sources = []
    added_images = []
    class FakeResearcher:
        def __init__(self):
            self.verbose = True
            self.websocket = object()
            # cfg must have attributes max_scraper_workers and scraper_rate_limit_delay
            self.cfg = types.SimpleNamespace(max_scraper_workers=1, scraper_rate_limit_delay=0)
        def add_research_sources(self, sources):
            added_sources.extend(sources)
        def add_research_images(self, imgs):
            added_images.extend(imgs)

    researcher = FakeResearcher()

    # Instantiate BrowserManager (its __init__ expects a researcher)
    bm = BrowserManager(researcher)
    # Provide a worker_pool (can be any object)
    bm.worker_pool = object()

    # Monkeypatch select_top_images on instance to return top 4
    def mock_select_top_images(imgs, k=4):
        assert imgs is images
        return imgs[:k]
    setattr(bm, "select_top_images", mock_select_top_images)

    result = await bm.browse_urls(["http://a", "http://b"])

    # Assertions
    assert result is scraped_content
    assert added_sources == scraped_content
    assert added_images == images[:4]

    # Expect four stream_output calls for verbose=True (urls, content, images, complete)
    assert len(stream_calls) == 4

    event_names = [c["args"][1] if len(c["args"]) > 1 else None for c in stream_calls]
    assert "scraping_urls" in event_names
    assert "scraping_content" in event_names
    assert "scraping_images" in event_names
    assert "scraping_complete" in event_names

    # Check that scraping_images call included True and the new_images list
    for c in stream_calls:
        if c["args"][1] == "scraping_images":
            args = c["args"]
            assert True in args
            assert any(isinstance(a, list) and a == images[:4] for a in args)
            break
    else:
        pytest.fail("scraping_images call not found")

@pytest.mark.asyncio
async def test_browse_urls_verbose_false_skips_stream_output(monkeypatch):
    browser_mod = import_browser_module()
    BrowserManager = getattr(browser_mod, "BrowserManager")

    stream_calls = []
    async def mock_stream_output(*args, **kwargs):
        stream_calls.append({"args": args, "kwargs": kwargs})

    scraped_content = [{"url": "http://c", "text": "C"}]
    images = []
    async def mock_scrape_urls(urls, cfg, worker_pool):
        return scraped_content, images

    monkeypatch.setattr(browser_mod, "stream_output", mock_stream_output, raising=False)
    monkeypatch.setattr(browser_mod, "scrape_urls", mock_scrape_urls, raising=False)

    added_sources = []
    added_images = []
    class FakeResearcher:
        def __init__(self):
            self.verbose = False
            self.websocket = None
            self.cfg = types.SimpleNamespace(max_scraper_workers=1, scraper_rate_limit_delay=0)
        def add_research_sources(self, sources):
            added_sources.extend(sources)
        def add_research_images(self, imgs):
            added_images.extend(imgs)

    researcher = FakeResearcher()
    bm = BrowserManager(researcher)
    bm.worker_pool = None

    setattr(bm, "select_top_images", lambda imgs, k=4: [])

    result = await bm.browse_urls(["http://c"])

    # When verbose is False, no stream_output calls should have been made
    assert stream_calls == []
    assert result is scraped_content
    assert added_sources == scraped_content
    assert added_images == []
