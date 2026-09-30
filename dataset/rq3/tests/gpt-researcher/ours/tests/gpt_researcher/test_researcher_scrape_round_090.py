import asyncio
from types import SimpleNamespace

import pytest

import gpt_researcher.skills.researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor


@pytest.mark.asyncio
async def test_verbose_none_vectorstore_round_090(monkeypatch):
    """
    - query_domains is None -> branch at line 811->812
    - researcher.verbose is True -> triggers stream_output (817->818)
    - researcher.vector_store is None -> skip load (831->832)
    - ensure prefetched_content is appended to scraped_content (829)
    """

    # Recording containers
    stream_called = {"called": False, "args": None}
    browse_called = {"called": False, "urls": None}

    # Patch stream_output in module to an async function that records calls
    async def fake_stream_output(channel, kind, message, websocket):
        stream_called["called"] = True
        stream_called["args"] = (channel, kind, message, websocket)
        # no external side effects

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Prepare researcher attributes: verbose True, websocket placeholder,
    # scraper_manager.browse_urls async function that records input and returns scraped list
    async def fake_browse_urls(urls):
        browse_called["called"] = True
        browse_called["urls"] = list(urls)
        return ["scraped_from_web"]

    scraper_manager = SimpleNamespace(browse_urls=fake_browse_urls)
    researcher_obj = SimpleNamespace(verbose=True, websocket="ws://fake", scraper_manager=scraper_manager, vector_store=None)

    # Instantiate conductor with our fake researcher
    conductor = ResearchConductor(researcher_obj)

    # Patch the instance method _search_relevant_source_urls to return predictable values
    async def fake_search_relevant_source_urls(sub_query, query_domains):
        # Ensure the function receives query_domains transformed to [] when None
        assert query_domains == []
        return (["http://example.com"], ["prefetched_text"])

    conductor._search_relevant_source_urls = fake_search_relevant_source_urls

    # Call the target async method
    result = await conductor._scrape_data_by_urls("some query", None)

    # Assertions: scraped content plus prefetched appended, stream_output called, browse called
    assert browse_called["called"] is True
    assert browse_called["urls"] == ["http://example.com"]
    assert stream_called["called"] is True
    # message fragment sanity check
    assert "Researching for relevant information" in stream_called["args"][2]
    assert result == ["scraped_from_web", "prefetched_text"]


@pytest.mark.asyncio
async def test_non_verbose_with_vectorstore_round_090(monkeypatch):
    """
    - query_domains provided -> skip None branch (811->814)
    - researcher.verbose is False -> do NOT call stream_output (817->826)
    - researcher.vector_store is present -> load should be called (831->834)
    - ensure vector_store.load receives the merged scraped_content list (829)
    """

    stream_called = {"called": False}
    browse_called = {"called": False}
    loaded = {"called": False, "received": None}

    # stream_output should not be invoked for verbose=False; provide an implementation that marks if called
    async def fake_stream_output(*args, **kwargs):
        stream_called["called"] = True

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Fake browse_urls returns initial scraped list
    async def fake_browse_urls(urls):
        browse_called["called"] = True
        return ["s1", "s2"]

    scraper_manager = SimpleNamespace(browse_urls=fake_browse_urls)

    # vector_store.load is synchronous in the code under test; make a simple recorder
    def fake_load(received_list):
        loaded["called"] = True
        # record the actual object passed so we can assert identity/mutation
        loaded["received"] = list(received_list)

    vector_store = SimpleNamespace(load=fake_load)

    researcher_obj = SimpleNamespace(verbose=False, websocket=None, scraper_manager=scraper_manager, vector_store=vector_store)
    conductor = ResearchConductor(researcher_obj)

    # Return a non-empty prefetched_content to validate merging
    async def fake_search_relevant_source_urls(sub_query, query_domains):
        # query_domains should be passed through unchanged
        assert query_domains == ["allowed.com"]
        return (["http://a", "http://b"], ["prefetched_one"])

    conductor._search_relevant_source_urls = fake_search_relevant_source_urls

    result = await conductor._scrape_data_by_urls("q2", ["allowed.com"])

    # stream_output must not be called
    assert stream_called["called"] is False
    # browse_urls must be used
    assert browse_called["called"] is True
    # vector_store.load must have been called with the merged list
    assert loaded["called"] is True
    assert loaded["received"] == ["s1", "s2", "prefetched_one"]
    # final return value should be the merged list as well
    assert result == ["s1", "s2", "prefetched_one"]
