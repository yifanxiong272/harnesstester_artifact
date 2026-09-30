# file: gpt_researcher/scraper/browser/nodriver_scraper.py:136-172
# asked: {"lines": [138, 139, 141, 142, 143, 144, 148, 149, 150, 152, 153, 154, 155, 157, 158, 160, 163, 167, 168, 170, 172], "branches": [[158, 160], [158, 163], [166, 170], [166, 172]]}
# gained: {"lines": [138, 139, 141, 142, 143, 144, 148, 149, 150, 152, 153, 154, 155, 157, 158, 160, 163, 167, 168, 170, 172], "branches": [[158, 160], [158, 163], [166, 170], [166, 172]]}

import sys
import types
import asyncio
import pytest

from gpt_researcher.scraper.browser.nodriver_scraper import NoDriverScraper


class FakeDriver:
    def __init__(self, name):
        self.name = name


class FakeZendriverModule(types.ModuleType):
    def __init__(self, name="zendriver", driver_name="fake"):
        super().__init__(name)
        self.last_config = None
        self._driver_name = driver_name

        # define Config as a simple class that stores passed args
        class Config:
            def __init__(self_inner, headless=False, browser_connection_timeout=0):
                self_inner.headless = headless
                self_inner.browser_connection_timeout = browser_connection_timeout

        async def start(config):
            # record config and return a FakeDriver instance
            self.last_config = config
            await asyncio.sleep(0)  # ensure it's an actual coroutine
            return FakeDriver(self._driver_name)

        self.Config = Config
        self.start = start


@pytest.mark.asyncio
async def test_get_browser_raises_import_error_when_zendriver_missing(monkeypatch):
    # Ensure zendriver is not importable
    monkeypatch.delitem(sys.modules, 'zendriver', raising=False)

    # Reset state
    NoDriverScraper.browsers = set()
    NoDriverScraper.browsers_lock = asyncio.Lock()

    with pytest.raises(ImportError) as excinfo:
        await NoDriverScraper.get_browser(headless=False)
    assert "The zendriver package is required" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_browser_creates_browser_when_none_exist(monkeypatch):
    fake_mod = FakeZendriverModule(driver_name="driver1")
    monkeypatch.setitem(sys.modules, 'zendriver', fake_mod)

    # Reset state
    NoDriverScraper.browsers = set()
    NoDriverScraper.browsers_lock = asyncio.Lock()

    browser = await NoDriverScraper.get_browser(headless=True)

    # Confirm returned object is a Browser and uses the fake driver
    assert isinstance(browser, NoDriverScraper.Browser)
    assert isinstance(browser.driver, FakeDriver)
    assert browser.driver.name == "driver1"

    # Ensure the zendriver.Config was called with correct args
    assert fake_mod.last_config is not None
    assert getattr(fake_mod.last_config, "headless") is True
    assert getattr(fake_mod.last_config, "browser_connection_timeout") == 10

    # Browser added to class set
    assert browser in NoDriverScraper.browsers
    # Clean up
    NoDriverScraper.browsers.clear()


@pytest.mark.asyncio
async def test_get_browser_creates_new_when_least_loaded_exceeds_threshold(monkeypatch):
    # Prepare a fake zendriver to be used when create_browser is called
    fake_mod = FakeZendriverModule(driver_name="driver2")
    monkeypatch.setitem(sys.modules, 'zendriver', fake_mod)

    # Reset state and lock
    NoDriverScraper.browsers = set()
    NoDriverScraper.browsers_lock = asyncio.Lock()

    # Create an existing browser with processing_count >= threshold
    existing_driver = FakeDriver("existing")
    existing_browser = NoDriverScraper.Browser(existing_driver)
    existing_browser.processing_count = NoDriverScraper.browser_load_threshold  # at threshold
    NoDriverScraper.browsers.add(existing_browser)

    # Ensure there's room to create more browsers
    NoDriverScraper.max_browsers = max(2, NoDriverScraper.max_browsers)

    new_browser = await NoDriverScraper.get_browser(headless=False)

    # Should have created a new browser (not the existing one)
    assert new_browser is not existing_browser
    assert isinstance(new_browser.driver, FakeDriver)
    assert new_browser.driver.name == "driver2"

    # Both browsers present in the set
    assert existing_browser in NoDriverScraper.browsers
    assert new_browser in NoDriverScraper.browsers
    assert len(NoDriverScraper.browsers) >= 2

    # Clean up
    NoDriverScraper.browsers.clear()


@pytest.mark.asyncio
async def test_get_browser_returns_least_loaded_browser_without_creating(monkeypatch):
    # Create a zendriver module whose start would raise if called (to detect unwanted creation)
    fake_mod = FakeZendriverModule(driver_name="should_not_be_started")
    async def start_raises(config):
        raise RuntimeError("start should not be called in this test")
    fake_mod.start = start_raises
    monkeypatch.setitem(sys.modules, 'zendriver', fake_mod)

    # Reset state and lock
    NoDriverScraper.browsers = set()
    NoDriverScraper.browsers_lock = asyncio.Lock()

    # Create two browsers with different processing counts, both under threshold
    d1 = FakeDriver("d1")
    d2 = FakeDriver("d2")
    b1 = NoDriverScraper.Browser(d1)
    b2 = NoDriverScraper.Browser(d2)
    b1.processing_count = 1
    b2.processing_count = 3
    NoDriverScraper.browsers.add(b1)
    NoDriverScraper.browsers.add(b2)

    # Ensure threshold is higher than both processing counts
    NoDriverScraper.browser_load_threshold = max(10, NoDriverScraper.browser_load_threshold)

    chosen = await NoDriverScraper.get_browser(headless=False)

    # Should return the browser with the least processing_count (b1)
    assert chosen is b1
    # Ensure no new browsers were added
    assert len(NoDriverScraper.browsers) == 2

    # Clean up
    NoDriverScraper.browsers.clear()
