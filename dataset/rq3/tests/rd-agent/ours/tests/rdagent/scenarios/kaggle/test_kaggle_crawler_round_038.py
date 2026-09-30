import json
from pathlib import Path
import importlib
import types
import pytest

from rdagent.scenarios.kaggle import kaggle_crawler


def test_crawl_descriptions_loads_md_round_038(tmp_path):
    # Setup: create directory and description.md to trigger first early return branch
    comp = "comp_md"
    comp_dir = tmp_path / comp
    comp_dir.mkdir()
    md_file = comp_dir / "description.md"
    md_text = "This is a test description"
    md_file.write_text(md_text)

    # Call
    res = kaggle_crawler.crawl_descriptions(comp, str(tmp_path), wait=0.0, force=False)

    # Assert the function returns the content of the markdown file
    assert isinstance(res, str)
    assert res == md_text


def test_crawl_descriptions_loads_json_round_038(tmp_path):
    # Setup: create a local JSON file to trigger second early return branch
    comp = "comp_json"
    data = {"a": 1, "b": "two"}
    json_file = tmp_path / f"{comp}.json"
    json_file.write_text(json.dumps(data))

    # Call
    res = kaggle_crawler.crawl_descriptions(comp, str(tmp_path), wait=0.0, force=False)

    # Assert the function returns the parsed JSON object
    assert isinstance(res, dict)
    assert res == data


class _SimpleElement:
    def __init__(self, inner_html=None, class_attr=None, find_map=None):
        self._inner = inner_html
        self._class = class_attr
        # find_map: dict of xpath -> element to return
        self._find_map = find_map or {}

    def find_element(self, by, value):
        # used for nested xpath chains; return mapped element or raise
        return self._find_map.get(value)

    def find_elements(self, by, value):
        # not used on these simple elements in our tests
        return []

    def get_attribute(self, name):
        if name == "innerHTML":
            return self._inner
        if name == "class":
            return self._class
        return None


class FakeSiteBody:
    def __init__(self, driver):
        # configured tokens
        self.driver = driver
        self.main_class = "mainClass"
        self.citation_class = "citeClass"
        # contents returned for overview
        self.contents = ["<p>content1</p>"]
        self.citation_html = "<span>cite content</span>"
        self.data_html = "<div>data content</div>"

        # Build nested elements for kaggle_description_css_selectors
        selector_elm = _SimpleElement(class_attr=f"x y {self.main_class}")
        first_content_elm = _SimpleElement(find_map={"./*[1]/*[1]": selector_elm})
        first_elm = _SimpleElement(find_map={"./*[1]/*[2]": first_content_elm})
        others_elm = _SimpleElement(find_map={"./*[1]": first_elm})
        self.abstract = _SimpleElement(find_map={"../*[2]": others_elm})

        citation_content_elm = _SimpleElement(class_attr=f"p q {self.citation_class}")
        self.citation = _SimpleElement(find_map={"./*[1]/*[2]/*[1]/*[1]": citation_content_elm})

    def find_element(self, by, value):
        # Provide the various single-element selectors used by the function
        if by == kaggle_crawler.By.ID and value == "abstract":
            return self.abstract
        if by == kaggle_crawler.By.ID and value == "citation":
            return self.citation
        if by == kaggle_crawler.By.CSS_SELECTOR and value == f".{self.citation_class}":
            return _SimpleElement(inner_html=self.citation_html)
        if by == kaggle_crawler.By.CSS_SELECTOR and value == f".{self.main_class}":
            # When asking for a single element (used on the data page)
            return _SimpleElement(inner_html=self.data_html)
        # Fallback: if asked for site-content, return self (the container)
        if by == kaggle_crawler.By.ID and value == "site-content":
            return self
        raise AssertionError(f"Unexpected find_element call: {by}, {value}")

    def find_elements(self, by, value):
        # Provide the lists used: subtitle anchors and the content blocks
        if by == kaggle_crawler.By.CSS_SELECTOR and value.startswith("a[href^"):
            # Two anchors: one subtitle and one 'Citation'
            class Anchor:
                def __init__(self, text):
                    self._text = text

                def find_elements(self, by, value):
                    # return a single child element whose innerHTML is the subtitle text
                    return [_SimpleElement(inner_html=self._text)]

            return [Anchor("Sub1"), Anchor("Citation")]
        if by == kaggle_crawler.By.CSS_SELECTOR and value == f".{self.main_class}":
            # Return the list of content blocks for overview
            return [_SimpleElement(inner_html=self.contents[0])]
        return []


class FakeDriver:
    def __init__(self):
        self.current_page = None
        self.quit_called = False
        self.site_body = FakeSiteBody(self)

    def get(self, url):
        # mark which page we're on by presence of '/data' in URL vs '/overview'
        if url.endswith("/data"):
            self.current_page = "data"
        else:
            self.current_page = "overview"

    def find_element(self, by, value):
        # The top-level driver.find_element is used to get the site_body and later data element
        # delegate to site_body for resolution
        return self.site_body.find_element(by, value)

    def find_elements(self, by, value):
        return self.site_body.find_elements(by, value)

    def quit(self):
        self.quit_called = True


def test_crawl_descriptions_full_flow_round_038(tmp_path, monkeypatch):
    # Ensure no local files exist so the function goes through the full webdriver flow
    comp = "comp_full"
    # monkeypatch time.sleep to avoid delays
    monkeypatch.setattr(kaggle_crawler.time, "sleep", lambda s: None)

    # Patch ChromeDriverManager to avoid network activity
    class FakeCM:
        def install(self):
            return "chromedriver"

    monkeypatch.setattr(kaggle_crawler, "ChromeDriverManager", FakeCM)

    # Patch Service to simple passthrough (the patched webdriver.Chrome will ignore it)
    class FakeService:
        def __init__(self, x):
            self.path = x

    monkeypatch.setattr(kaggle_crawler, "Service", FakeService)

    # Patch webdriver.Chrome to return our FakeDriver
    class FakeWebdriverModule:
        def Chrome(self, *args, **kwargs):
            return FakeDriver()

    monkeypatch.setattr(kaggle_crawler, "webdriver", FakeWebdriverModule())

    # Ensure module has an 'options' symbol (the function references it when creating Chrome)
    monkeypatch.setattr(kaggle_crawler, "options", object(), raising=False)

    # Execute
    res = kaggle_crawler.crawl_descriptions(comp, str(tmp_path), wait=0.0, force=False)

    # Validate the returned structure and its contents
    assert isinstance(res, dict)
    # keys: Sub1 from subtitles, Citation, and Data Description
    assert res.get("Sub1") is not None
    assert res.get("Citation") is not None
    assert res.get("Data Description") is not None

    # Ensure the specific expected pieces appear
    assert "content1" in res["Sub1"] or "content1" in res["Sub1"]
    assert "cite content" in res["Citation"]
    assert "data content" in res["Data Description"]

    # Ensure file was written
    out_file = tmp_path / f"{comp}.json"
    assert out_file.exists()
    loaded = json.loads(out_file.read_text())
    assert loaded == res


# Ensure tests are deterministic and do not call external services by design of the fakes above
