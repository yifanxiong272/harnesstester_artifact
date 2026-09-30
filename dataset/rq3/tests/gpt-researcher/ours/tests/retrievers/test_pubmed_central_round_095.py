import types
from gpt_researcher.retrievers.pubmed_central.pubmed_central import PubMedCentralSearch


def test_search_no_ids_round_095():
    """When _search_articles returns an empty list, search should return None."""
    # Create instance without calling __init__ to avoid side effects
    instance = object.__new__(PubMedCentralSearch)

    # Patch instance methods deterministically
    instance._search_articles = lambda max_results: []

    result = instance.search(5)

    assert result is None


def test_search_ids_no_content_round_095():
    """When there are article ids but _fetch_full_text returns falsy values, search returns an empty list."""
    instance = object.__new__(PubMedCentralSearch)

    instance._search_articles = lambda max_results: ["PMC0001", "PMC0002"]
    # All fetches return None (falsy)
    instance._fetch_full_text = lambda article_id: None

    result = instance.search(max_results=2)

    # Expect an empty list (not None) because there were article ids but no content appended
    assert isinstance(result, list)
    assert result == []


def test_search_ids_mixed_content_round_095():
    """Mixed truthy and falsy fetch results: only truthy results are appended and returned in order."""
    instance = object.__new__(PubMedCentralSearch)

    article_ids = ["PMC_A", "PMC_B", "PMC_C"]
    instance._search_articles = lambda max_results: article_ids

    # Prepare deterministic payloads preserving expected shape
    payloads = {
        "PMC_A": {"url": "https://example.org/A", "raw_content": "Content A"},
        "PMC_B": None,
        "PMC_C": {"url": "https://example.org/C", "raw_content": "Content C"},
    }
    instance._fetch_full_text = lambda article_id: payloads[article_id]

    result = instance.search(max_results=10)

    # Only A and C should be present, in the same order as article_ids
    assert isinstance(result, list)
    assert result == [payloads["PMC_A"], payloads["PMC_C"]]
