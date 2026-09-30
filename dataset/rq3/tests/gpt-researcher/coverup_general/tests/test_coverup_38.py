# file: gpt_researcher/scraper/browser/browser.py:191-224
# asked: {"lines": [192, 194, 195, 196, 198, 199, 200, 201, 203, 205, 206, 207, 208, 209, 210, 211, 213, 214, 216, 218, 220, 221, 222, 224], "branches": [[205, 206], [205, 208], [208, 209], [208, 213]]}
# gained: {"lines": [192, 194, 195, 196, 198, 199, 200, 201, 203, 205, 206, 207, 208, 209, 210, 211, 213, 214, 216, 218, 220, 221, 222, 224], "branches": [[205, 206], [205, 208], [208, 209], [208, 213]]}

import pytest

import gpt_researcher.scraper.browser.browser as browser_mod
from gpt_researcher.scraper.browser.browser import BrowserScraper


class DummyDriver:
    def __init__(self, execute_result=None):
        self.get_calls = []
        self.execute_result = execute_result

    def get(self, url):
        self.get_calls.append(url)

    def execute_script(self, script):
        if self.execute_result is not None:
            return self.execute_result
        return ""


def _noop_import_selenium(self):
    # used to avoid real selenium imports / side effects during BrowserScraper init
    return None


def _ensure_fake_ec_and_by(monkeypatch):
    class FakeEC:
        @staticmethod
        def presence_of_element_located(arg):
            # return a callable or any object; Waiting.*.until may ignore it
            return lambda driver: True

    class FakeBy:
        TAG_NAME = "body"

    # allow creating these attributes if they don't exist
    monkeypatch.setattr(browser_mod, "EC", FakeEC, raising=False)
    monkeypatch.setattr(browser_mod, "By", FakeBy, raising=False)


def test_scrape_text_with_selenium_timeout(monkeypatch):
    # Arrange: prevent selenium import side effects
    monkeypatch.setattr(browser_mod.BrowserScraper, "_import_selenium", _noop_import_selenium)

    # Provide EC and By used in condition evaluation (if referenced)
    _ensure_fake_ec_and_by(monkeypatch)

    # Make a custom TimeoutException class inside module to be caught by the method
    class CustomTimeout(Exception):
        pass

    monkeypatch.setattr(browser_mod, "TimeoutException", CustomTimeout, raising=False)

    # Configure WebDriverWait to raise the TimeoutException when until() is called
    class WaitingThatTimesOut:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, condition):
            raise CustomTimeout("simulated timeout")

    monkeypatch.setattr(browser_mod, "WebDriverWait", WaitingThatTimesOut, raising=False)

    # Create scraper and set a dummy driver that records get() calls
    url = "http://example.com/"
    scraper = BrowserScraper(url)
    dummy_driver = DummyDriver()
    scraper.driver = dummy_driver

    # Act
    result = scraper.scrape_text_with_selenium()

    # Assert
    assert result == ("Page load timed out", [], "")
    assert dummy_driver.get_calls == [url]


def test_scrape_text_with_selenium_pdf_branch(monkeypatch):
    # Arrange
    monkeypatch.setattr(browser_mod.BrowserScraper, "_import_selenium", _noop_import_selenium)
    _ensure_fake_ec_and_by(monkeypatch)

    # WebDriverWait that succeeds
    class WaitingThatSucceeds:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, condition):
            return True

    monkeypatch.setattr(browser_mod, "WebDriverWait", WaitingThatSucceeds, raising=False)

    # Replace scrape_pdf_with_pymupdf to avoid real network/file operations
    captured = {}
    def fake_scrape_pdf_with_pymupdf(url):
        captured["called_with"] = url
        return "PDF_TEXT_CONTENT"

    monkeypatch.setattr(browser_mod, "scrape_pdf_with_pymupdf", fake_scrape_pdf_with_pymupdf, raising=False)

    # Make sure _scroll_to_bottom is called
    called = {"scrolled": False}
    def fake_scroll(self):
        called["scrolled"] = True

    monkeypatch.setattr(browser_mod.BrowserScraper, "_scroll_to_bottom", fake_scroll)

    url = "https://somehost/somefile.pdf"
    scraper = BrowserScraper(url)
    dummy_driver = DummyDriver()
    scraper.driver = dummy_driver

    # Act
    result = scraper.scrape_text_with_selenium()

    # Assert
    assert result == ("PDF_TEXT_CONTENT", [], "")
    assert captured["called_with"] == url
    assert called["scrolled"] is True
    assert dummy_driver.get_calls == [url]


def test_scrape_text_with_selenium_arxiv_branch(monkeypatch):
    # Arrange
    monkeypatch.setattr(browser_mod.BrowserScraper, "_import_selenium", _noop_import_selenium)
    _ensure_fake_ec_and_by(monkeypatch)

    class WaitingThatSucceeds:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, condition):
            return True

    monkeypatch.setattr(browser_mod, "WebDriverWait", WaitingThatSucceeds, raising=False)

    # Replace scrape_pdf_with_arxiv and capture the doc number passed
    captured = {}
    def fake_scrape_pdf_with_arxiv(doc_num):
        captured["doc_num"] = doc_num
        return "ARXIV_TEXT"

    monkeypatch.setattr(browser_mod, "scrape_pdf_with_arxiv", fake_scrape_pdf_with_arxiv, raising=False)

    # Ensure scrolling happens
    called = {"scrolled": False}
    monkeypatch.setattr(browser_mod.BrowserScraper, "_scroll_to_bottom", lambda self: called.__setitem__("scrolled", True))

    url = "https://arxiv.org/abs/1234.5678"
    scraper = BrowserScraper(url)
    scraper.driver = DummyDriver()

    # Act
    result = scraper.scrape_text_with_selenium()

    # Assert
    assert result == ("ARXIV_TEXT", [], "")
    assert captured["doc_num"] == "1234.5678"
    assert called["scrolled"] is True


def test_scrape_text_with_selenium_html_branch(monkeypatch):
    # Arrange
    monkeypatch.setattr(browser_mod.BrowserScraper, "_import_selenium", _noop_import_selenium)
    _ensure_fake_ec_and_by(monkeypatch)

    class WaitingThatSucceeds:
        def __init__(self, driver, timeout):
            self.driver = driver
            self.timeout = timeout

        def until(self, condition):
            return True

    monkeypatch.setattr(browser_mod, "WebDriverWait", WaitingThatSucceeds, raising=False)

    # Prepare dummy HTML and driver that returns it via execute_script
    html = "<html><head><title>MyTitle</title></head><body><p>hello</p><img src='a.png'/></body></html>"
    dummy_driver = DummyDriver(execute_result=html)

    # Replace BeautifulSoup cleaning and helpers to deterministic outputs
    def fake_clean_soup(soup):
        return soup

    monkeypatch.setattr(browser_mod, "clean_soup", fake_clean_soup, raising=False)
    monkeypatch.setattr(browser_mod, "get_text_from_soup", lambda soup: "EXTRACTED_TEXT", raising=False)
    monkeypatch.setattr(browser_mod, "get_relevant_images", lambda soup, url: ["https://site/a.png"], raising=False)
    monkeypatch.setattr(browser_mod, "extract_title", lambda soup: "MyTitle-Extracted", raising=False)

    # Ensure scrolling is invoked
    scrolled = {"yes": False}
    monkeypatch.setattr(browser_mod.BrowserScraper, "_scroll_to_bottom", lambda self: scrolled.__setitem__("yes", True))

    url = "https://example.org/page"
    scraper = BrowserScraper(url)
    scraper.driver = dummy_driver

    # Act
    text, images, title = scraper.scrape_text_with_selenium()

    # Assert
    assert text == "EXTRACTED_TEXT"
    assert images == ["https://site/a.png"]
    assert title == "MyTitle-Extracted"
    assert dummy_driver.get_calls == [url]
    assert scrolled["yes"] is True
