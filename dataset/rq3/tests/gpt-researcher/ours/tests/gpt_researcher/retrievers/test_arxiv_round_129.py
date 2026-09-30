import importlib
import sys
import types
from types import SimpleNamespace
import pytest


def make_fake_arxiv(results_iterable, search_call_record):
    """Create a fake 'arxiv' module-like object.

    - results_iterable: the iterable that Client().results(...) should return
    - search_call_record: a list object where the Search kwargs will be appended
    """
    fake = types.ModuleType("arxiv")

    # Simple SortCriterion container
    fake.SortCriterion = SimpleNamespace(Relevance="RELEVANCE", SubmittedDate="SUBMITTED")

    # Search function records kwargs and returns a sentinel object
    def Search(**kwargs):
        search_call_record.append(kwargs)
        return SimpleNamespace(_search_kwargs=kwargs)

    fake.Search = Search

    class Client:
        def __init__(self):
            pass

        def results(self, search_obj):
            # ignore search_obj content; return the predetermined iterable
            return results_iterable

    fake.Client = Client
    return fake


def import_target_with_fake(fake_arxiv):
    # Ensure our fake 'arxiv' is used when importing the target module
    sys.modules["arxiv"] = fake_arxiv
    # Remove any previously imported target to force re-import with our fake
    target_name = "gpt_researcher.retrievers.arxiv.arxiv"
    if target_name in sys.modules:
        del sys.modules[target_name]
    module = importlib.import_module(target_name)
    return module


def test_search_empty_round_129(monkeypatch):
    # Prepare fake arxiv with no search results and capture Search kwargs
    search_calls = []
    fake = make_fake_arxiv(results_iterable=[], search_call_record=search_calls)

    # Import target module with fake injected
    module = import_target_with_fake(fake)

    # Construct ArxivSearch with default sort (should pick Relevance)
    ArxivSearch = module.ArxivSearch
    instance = ArxivSearch(query="quantum computing")

    # Sanity: default sort value should match fake.SortCriterion.Relevance
    assert instance.sort == fake.SortCriterion.Relevance

    # Run search and expect empty list
    result = instance.search(max_results=2)
    assert result == []

    # Ensure Search was called with expected kwargs
    assert len(search_calls) == 1
    called_kwargs = search_calls[0]
    assert called_kwargs["query"] == "quantum computing"
    assert called_kwargs["max_results"] == 2
    # sort_by will be the instance.sort value
    assert called_kwargs["sort_by"] == fake.SortCriterion.Relevance


def test_search_results_round_129(monkeypatch):
    # Prepare two fake result objects to be returned by Client.results
    fake_results = [
        SimpleNamespace(title="Paper One", pdf_url="http://one.pdf", summary="Summary one"),
        SimpleNamespace(title="Paper Two", pdf_url="http://two.pdf", summary="Summary two"),
    ]
    search_calls = []
    fake = make_fake_arxiv(results_iterable=fake_results, search_call_record=search_calls)

    # Import target with fake arxiv module
    module = import_target_with_fake(fake)
    ArxivSearch = module.ArxivSearch

    # Use explicit 'SubmittedDate' sort to hit that branch in __init__
    instance = ArxivSearch(query="ml", sort="SubmittedDate")
    # Confirm the instance.sort was set to the SubmittedDate value
    assert instance.sort == fake.SortCriterion.SubmittedDate

    out = instance.search(max_results=5)

    # We expect two mapped dicts corresponding to the fake_results
    assert isinstance(out, list)
    assert len(out) == 2

    assert out[0]["title"] == "Paper One"
    assert out[0]["href"] == "http://one.pdf"
    assert out[0]["body"] == "Summary one"

    assert out[1]["title"] == "Paper Two"
    assert out[1]["href"] == "http://two.pdf"
    assert out[1]["body"] == "Summary two"

    # Ensure Search captured the expected parameters
    assert len(search_calls) == 1
    called_kwargs = search_calls[0]
    assert called_kwargs["query"] == "ml"
    assert called_kwargs["max_results"] == 5
    assert called_kwargs["sort_by"] == fake.SortCriterion.SubmittedDate


def test_invalid_sort_round_129(monkeypatch):
    # Minimal fake arxiv to satisfy import; we don't need real results here
    fake = make_fake_arxiv(results_iterable=[], search_call_record=[])
    module = import_target_with_fake(fake)
    ArxivSearch = module.ArxivSearch

    # Invalid sort should raise the assertion in __init__
    with pytest.raises(AssertionError) as exc:
        ArxivSearch(query="x", sort="NotAValidSort")
    assert "Invalid sort criterion" in str(exc.value)
