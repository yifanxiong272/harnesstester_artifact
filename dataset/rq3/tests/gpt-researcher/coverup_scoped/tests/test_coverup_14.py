# file: gpt_researcher/skills/researcher.py:580-652
# asked: {"lines": [591, 593, 595, 598, 599, 600, 601, 602, 603, 606, 607, 608, 609, 610, 611, 615, 616, 619, 620, 621, 623, 624, 625, 626, 627, 628, 631, 633, 634, 635, 636, 637, 638, 639, 641, 643, 644, 645, 646, 647, 648, 649, 650, 652], "branches": [[606, 607], [606, 615], [619, 620], [619, 633], [623, 624], [623, 631], [634, 635], [634, 641], [645, 646], [645, 652]]}
# gained: {"lines": [591, 593, 595, 598, 599, 600, 601, 602, 603, 606, 607, 608, 609, 610, 611, 615, 616, 619, 620, 621, 623, 624, 625, 626, 627, 628, 631, 633, 634, 635, 636, 637, 638, 639, 641, 643, 644, 645, 646, 647, 648, 649, 650, 652], "branches": [[606, 607], [606, 615], [619, 620], [619, 633], [623, 624], [623, 631], [634, 635], [645, 646]]}

import importlib
from types import SimpleNamespace
import pytest

# Helper to import the researcher module and ensure stream_output is patched before researcher imports it.
def import_researcher_and_patch_stream(fake_stream_output):
    utils_candidates = [
        "gpt_researcher.actions.utils",
        "gpt_researcher.gpt_researcher.actions.utils",
    ]
    researcher_candidates = [
        "gpt_researcher.skills.researcher",
        "gpt_researcher.gpt_researcher.skills.researcher",
    ]

    utils_mod = None
    for u in utils_candidates:
        try:
            utils_mod = importlib.import_module(u)
            break
        except ModuleNotFoundError:
            continue

    # If utils module found, patch stream_output there so researcher import picks it up.
    if utils_mod is not None:
        setattr(utils_mod, "stream_output", fake_stream_output)

    researcher_mod = None
    for r in researcher_candidates:
        try:
            researcher_mod = importlib.import_module(r)
            break
        except ModuleNotFoundError:
            continue

    if researcher_mod is None:
        raise ModuleNotFoundError(
            "Could not import researcher module from expected candidate paths."
        )

    # Ensure researcher module uses the patched stream_output as an attribute if it imported earlier.
    # Overwrite in researcher module as well to be safe.
    setattr(researcher_mod, "stream_output", fake_stream_output)

    ResearchConductor = getattr(researcher_mod, "ResearchConductor")
    return ResearchConductor


@pytest.mark.asyncio
async def test_execute_mcp_research_with_results_verbose_true(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    ResearchConductor = import_researcher_and_patch_stream(fake_stream_output)

    # Define a retriever that returns results
    class GoodRetriever:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            # store values to assert they are passed in correctly (optional)
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher

        def search(self, max_results=None):
            # return a non-empty result list
            return [{"id": 1, "text": "result1"}, {"id": 2, "text": "result2"}]

    # Create a dummy researcher with required attributes
    cfg = SimpleNamespace(max_search_results_per_query=5)
    dummy_researcher = SimpleNamespace(
        headers={"auth": "token"},
        query_domains=["example.com"],
        websocket="wss://example",
        verbose=True,
        cfg=cfg,
    )

    conductor = ResearchConductor(dummy_researcher)

    results = await conductor._execute_mcp_research(GoodRetriever, "some query")

    # Assert the results are returned as-is
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["text"] == "result1"

    # Because verbose=True, we expect two stream_output calls:
    event_names = [call[1] for call in calls]
    assert "mcp_retrieval_stage1" in event_names
    assert "mcp_research_complete" in event_names


@pytest.mark.asyncio
async def test_execute_mcp_research_with_results_verbose_false(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    ResearchConductor = import_researcher_and_patch_stream(fake_stream_output)

    class GoodRetriever:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            pass

        def search(self, max_results=None):
            return ["only_result"]

    cfg = SimpleNamespace(max_search_results_per_query=3)
    dummy_researcher = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=False,  # stream_output should NOT be invoked
        cfg=cfg,
    )

    conductor = ResearchConductor(dummy_researcher)

    results = await conductor._execute_mcp_research(GoodRetriever, "q2")

    assert results == ["only_result"]
    # verbose is False so stream_output should not have been called
    assert calls == []


@pytest.mark.asyncio
async def test_execute_mcp_research_no_results_verbose_true(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    ResearchConductor = import_researcher_and_patch_stream(fake_stream_output)

    class EmptyRetriever:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            pass

        def search(self, max_results=None):
            return []  # no results

    cfg = SimpleNamespace(max_search_results_per_query=2)
    dummy_researcher = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket="ws",
        verbose=True,
        cfg=cfg,
    )

    conductor = ResearchConductor(dummy_researcher)

    results = await conductor._execute_mcp_research(EmptyRetriever, "no results query")

    assert results == []  # should return empty list when no results

    event_names = [call[1] for call in calls]
    assert "mcp_retrieval_stage1" in event_names
    assert "mcp_no_results" in event_names


@pytest.mark.asyncio
async def test_execute_mcp_research_search_raises_exception(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    ResearchConductor = import_researcher_and_patch_stream(fake_stream_output)

    class BadRetriever:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            pass

        def search(self, max_results=None):
            raise RuntimeError("simulated search error")

    cfg = SimpleNamespace(max_search_results_per_query=1)
    dummy_researcher = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=True,
        cfg=cfg,
    )

    conductor = ResearchConductor(dummy_researcher)

    results = await conductor._execute_mcp_research(BadRetriever, "will error")

    # On exception, function should return empty list
    assert results == []

    # Because verbose True and error occurred, we expect an "mcp_research_error" in stream outputs
    event_names = [call[1] for call in calls]
    assert "mcp_research_error" in event_names
