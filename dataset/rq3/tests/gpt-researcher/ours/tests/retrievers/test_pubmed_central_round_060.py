import xml.etree.ElementTree as ET
import requests
import pytest

from gpt_researcher.retrievers.pubmed_central.pubmed_central import PubMedCentralSearch


class DummyResponse:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise requests.HTTPError(f"status: {self._status}")


def _make_mock_get(response_text: str, status: int = 200):
    def _mock_get(url, params=None):
        # ensure params shape preserved
        assert isinstance(params, dict)
        return DummyResponse(response_text, status=status)

    return _mock_get


def test_fetch_full_text_pmc_db_articleid_starting_pmc_round_060(monkeypatch):
    """
    Verify normal successful parsing when db_type is 'pmc' and article_id starts with 'PMC'.
    This covers extracting title, abstract, body and the branch that produces a URL using the article_id directly.
    """
    xml = (
        "<article>"
        "  <front>"
        "    <article-meta>"
        "      <title-group><article-title>Test Title</article-title></title-group>"
        "      <abstract><p>Abstract part one.</p><p>Abstract part two.</p></abstract>"
        "    </article-meta>"
        "  </front>"
        "  <body>"
        "    <sec><p>Body paragraph 1.</p></sec>"
        "  </body>"
        "</article>"
    )

    monkeypatch.setattr(
        "gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get",
        _make_mock_get(xml),
    )

    # Construct with actual __init__ signature, then set attributes expected by _fetch_full_text
    searcher = PubMedCentralSearch("q", [])
    searcher.api_key = "KEY"
    searcher.db_type = "pmc"
    # base_fetch_url can be any string; mock ignores it but ensure attribute exists
    searcher.base_fetch_url = "http://example.com/fetch"

    result = searcher._fetch_full_text("PMC123")

    assert isinstance(result, dict)
    assert result["title"] == "Test Title"
    # Abstract text should contain both parts joined by space
    assert "Abstract part one." in result["body"]
    assert "Body paragraph 1." in result["body"]
    # When db_type is 'pmc' or article_id starts with PMC the url uses the article_id as given
    assert result["href"].endswith("/PMC123/")
    assert result["href"] == result["url"]


def test_fetch_full_text_nonpmc_db_articleid_missing_pmc_prefix_round_060(monkeypatch):
    """
    Verify behavior when db_type is not 'pmc' and article_id does not start with 'PMC'.
    This should exercise the else-branch that prefixes 'PMC' to the article id for the URL formation.
    Also test when title is missing and abstract is missing, only body exists.
    """
    xml = (
        "<article>"
        "  <body>"
        "    <sec><p>Only body text.</p></sec>"
        "  </body>"
        "</article>"
    )

    monkeypatch.setattr(
        "gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get",
        _make_mock_get(xml),
    )

    searcher = PubMedCentralSearch("q", [])
    # set attributes expected by _fetch_full_text
    searcher.api_key = "KEY"
    searcher.db_type = "not_pmc"
    searcher.base_fetch_url = "http://example.com/fetch"

    result = searcher._fetch_full_text("123456")

    assert isinstance(result, dict)
    # No title element -> empty title string
    assert result["title"] == ""
    # Body text should be present
    assert "Only body text." in result["body"]
    # When not pmc and id doesn't start with PMC, code prefixes PMC
    assert result["href"].endswith("/PMC123456/")


def test_fetch_full_text_parse_error_round_060(monkeypatch):
    """
    Simulate ET.ParseError being raised to exercise the inner except block that returns None.
    """
    # Provide a normal response but force ET.fromstring to raise ParseError
    monkeypatch.setattr(
        "gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get",
        _make_mock_get("<invalid></xml>"),
    )

    # Patch the ET.fromstring in the module under test to raise ET.ParseError
    def _raise_parse_error(text):
        raise ET.ParseError("mock parse error")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.pubmed_central.pubmed_central.ET.fromstring",
        _raise_parse_error,
    )

    searcher = PubMedCentralSearch("q", [])
    searcher.api_key = "KEY"
    searcher.db_type = "pmc"
    searcher.base_fetch_url = "http://example.com/fetch"

    result = searcher._fetch_full_text("PMC9")
    assert result is None


def test_fetch_full_text_request_exception_round_060(monkeypatch):
    """
    Simulate requests.get raising a RequestException to exercise the outer except block that returns None.
    """

    def _raise_request_exc(url, params=None):
        # preserve param shape
        assert isinstance(params, dict)
        raise requests.RequestException("network error")

    monkeypatch.setattr(
        "gpt_researcher.retrievers.pubmed_central.pubmed_central.requests.get",
        _raise_request_exc,
    )

    searcher = PubMedCentralSearch("q", [])
    searcher.api_key = "KEY"
    searcher.db_type = "pmc"
    searcher.base_fetch_url = "http://example.com/fetch"

    result = searcher._fetch_full_text("PMC_ERR")
    assert result is None
