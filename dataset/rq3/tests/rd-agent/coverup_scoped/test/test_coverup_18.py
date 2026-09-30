# file: rdagent/scenarios/kaggle/kaggle_crawler.py:35-107
# asked: {"lines": [38, 39, 40, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53, 56, 57, 58, 59, 60, 61, 62, 64, 66, 67, 68, 69, 70, 71, 74, 75, 76, 78, 80, 83, 84, 85, 86, 87, 89, 90, 91, 94, 95, 96, 98, 99, 100, 101, 102, 104, 105, 106, 107], "branches": [[38, 39], [38, 42], [42, 43], [42, 48], [58, 59], [58, 64], [60, 61], [60, 62], [85, 86], [85, 89], [90, 91], [90, 94]]}
# gained: {"lines": [38, 39, 40, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53, 56, 57, 58, 59, 60, 61, 62, 64, 66, 67, 68, 69, 70, 71, 74, 75, 76, 78, 80, 83, 84, 85, 86, 87, 89, 90, 91, 94, 95, 96, 98, 99, 100, 101, 102, 104, 105, 106, 107], "branches": [[38, 39], [38, 42], [42, 43], [42, 48], [58, 59], [58, 64], [60, 61], [60, 62], [85, 86], [85, 89], [90, 91], [90, 94]]}

import json
import types
from pathlib import Path

import pytest

from rdagent.scenarios.kaggle.kaggle_crawler import crawl_descriptions


class FakeElement:
    def __init__(self, innerHTML="", class_attr="", children=None, xpath_map=None, css_map=None, id_map=None):
        self._innerHTML = innerHTML
        self._class = class_attr
        self._children = children or []
        self._xpath_map = xpath_map or {}
        self._css_map = css_map or {}
        self._id_map = id_map or {}

    def find_element(self, by, value):
        # XPath map
        if value in self._xpath_map:
            return self._xpath_map[value]
        # ID lookup
        if value in self._id_map:
            return self._id_map[value]
        # CSS selector exact match
        if value in self._css_map:
            v = self._css_map[value]
            return v[0] if isinstance(v, list) else v
        raise Exception(f"No element for find_element({by}, {value}) on FakeElement")

    def find_elements(self, by, value):
        if value in self._css_map:
            v = self._css_map[value]
            return v if isinstance(v, list) else [v]
        if value in self._xpath_map:
            v = self._xpath_map[value]
            return v if isinstance(v, list) else [v]
        if value == ".//*":
            return self._children
        return []

    def get_attribute(self, name):
        if name == "innerHTML":
            return self._innerHTML
        if name == "class":
            return self._class
        return ""


class FakeWebDriver:
    def __init__(self, site_body, data_element):
        self._site_body = site_body
        self._data_element = data_element
        self._got_urls = []

    def get(self, url):
        self._got_urls.append(url)

    def find_element(self, by, value):
        # site-content request
        if value == "site-content":
            return self._site_body
        # If last fetched URL is data page and a CSS class selector is requested, return data_element
        if isinstance(value, str) and value.startswith(".") and self._got_urls and "/data" in self._got_urls[-1]:
            return self._data_element
        # Otherwise delegate to site_body
        return self._site_body.find_element(by, value)

    def quit(self):
        pass


@pytest.mark.parametrize("competition", ["test_competition"])
def test_load_description_md_early_return(tmp_path, competition):
    comp_dir = tmp_path / competition
    comp_dir.mkdir()
    desc_file = comp_dir / "description.md"
    content = "# Title\n\nSome description"
    desc_file.write_text(content)

    result = crawl_descriptions(competition=competition, local_data_path=str(tmp_path), wait=0.0, force=False)
    assert isinstance(result, str)
    assert result == content


@pytest.mark.parametrize("competition", ["test_competition_json"])
def test_load_json_early_return(tmp_path, competition):
    data = {"A": "1", "B": "2"}
    json_file = tmp_path / f"{competition}.json"
    json_file.write_text(json.dumps(data))

    result = crawl_descriptions(competition=competition, local_data_path=str(tmp_path), wait=0.0, force=False)
    assert isinstance(result, dict)
    assert result == data


def test_crawl_descriptions_main_flow(tmp_path, monkeypatch):
    competition = "complex_comp"
    local_data_path = str(tmp_path)

    assert not (tmp_path / competition).exists()
    assert not (tmp_path / f"{competition}.json").exists()

    # subtitles: two real subtitles and a final "Citation" subtitle
    child1 = FakeElement(innerHTML="Subtitle One")
    child2 = FakeElement(innerHTML="Subtitle Two")
    child3 = FakeElement(innerHTML="Citation")
    anchor1 = FakeElement(children=[child1])
    anchor1._xpath_map[".//*"] = [child1]
    anchor2 = FakeElement(children=[child2])
    anchor2._xpath_map[".//*"] = [child2]
    anchor3 = FakeElement(children=[child3])
    anchor3._xpath_map[".//*"] = [child3]
    anchors = [anchor1, anchor2, anchor3]

    # main content elements corresponding to the two non-citation subtitles
    content1 = FakeElement(innerHTML="<p>Content One</p>")
    content2 = FakeElement(innerHTML="<p>Content Two</p>")

    # Build nested structure to extract main_class
    selector_elm = FakeElement(class_attr="foo bar mainclass")
    first_content_elm = FakeElement(xpath_map={"./*[1]/*[1]": selector_elm})
    first_elm = FakeElement(xpath_map={"./*[1]/*[2]": first_content_elm})
    others_elm = FakeElement(xpath_map={"./*[1]": first_elm})
    ab_elm = FakeElement(xpath_map={"../*[2]": others_elm})

    # Citation class element
    citation_content_elm = FakeElement(class_attr="x y citationclass")
    citation_elm = FakeElement(xpath_map={"./*[1]/*[2]/*[1]/*[1]": citation_content_elm})

    site_body = FakeElement()
    site_body._css_map[f"a[href^='/competitions/{competition}/overview/']"] = anchors
    site_body._id_map["abstract"] = ab_elm
    site_body._id_map["citation"] = citation_elm
    site_body._css_map[".mainclass"] = [content1, content2]
    citation_html_element = FakeElement(innerHTML="<p>Citation HTML</p>")
    site_body._css_map[".citationclass"] = citation_html_element

    data_element = FakeElement(innerHTML="<div>Data Description HTML</div>")

    fake_driver = FakeWebDriver(site_body=site_body, data_element=data_element)

    # Monkeypatch webdriver.Chrome to return fake_driver
    monkeypatch.setattr("rdagent.scenarios.kaggle.kaggle_crawler.webdriver.Chrome", lambda *a, **k: fake_driver)
    # Patch ChromeDriverManager to avoid network
    monkeypatch.setattr(
        "rdagent.scenarios.kaggle.kaggle_crawler.ChromeDriverManager",
        lambda *a, **k: types.SimpleNamespace(install=lambda: "/tmp/chromedriver"),
    )
    # Patch Service
    monkeypatch.setattr("rdagent.scenarios.kaggle.kaggle_crawler.Service", lambda *a, **k: None)
    # Patch time.sleep to no-op
    monkeypatch.setattr("rdagent.scenarios.kaggle.kaggle_crawler.time", types.SimpleNamespace(sleep=lambda _: None))

    result = crawl_descriptions(competition=competition, local_data_path=local_data_path, wait=0.0, force=False)

    assert isinstance(result, dict)
    # Should have keys for each subtitle (two contents + Citation) and Data Description
    assert "Subtitle One" in result
    assert "Subtitle Two" in result
    assert "Citation" in result
    assert "Data Description" in result

    assert result["Subtitle One"] == "<p>Content One</p>"
    assert result["Subtitle Two"] == "<p>Content Two</p>"
    assert result["Citation"] == "<p>Citation HTML</p>"
    assert result["Data Description"] == "<div>Data Description HTML</div>"

    json_path = Path(local_data_path) / f"{competition}.json"
    assert json_path.exists()
    loaded = json.loads(json_path.read_text())
    assert loaded == result
