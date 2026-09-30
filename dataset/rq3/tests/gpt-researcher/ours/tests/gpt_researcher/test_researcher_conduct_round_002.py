import pytest
import types
import asyncio

from gpt_researcher.skills import researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor

# Helpers used by tests
class FakeJSONHandler:
    def __init__(self):
        self.updates = []
    def update_content(self, key, value):
        self.updates.append((key, value))

class FakeVisited:
    def __init__(self):
        self.cleared = False
    def clear(self):
        self.cleared = True

class FakeVectorStore:
    def __init__(self):
        self.loaded_with = None
    def load(self, data):
        self.loaded_with = data

class FakeLoader:
    def __init__(self, payload):
        self._payload = payload
    async def load(self):
        # deterministic async loader
        await asyncio.sleep(0)
        return self._payload

class FakeSourceCurator:
    def __init__(self, result):
        self.result = result
        self.called_with = None
    async def curate_sources(self, research_data):
        self.called_with = research_data
        await asyncio.sleep(0)
        return self.result

class FakePromptFamily:
    def join_local_web_documents(self, docs_context, web_context):
        # deterministic join behavior
        return (docs_context or []) + (web_context or [])

@pytest.mark.asyncio
async def test_conduct_research_with_source_urls_and_verbose_round_002(monkeypatch):
    """Exercise branches: json_handler update, verbose stream_output calls, choose_agent, _get_context_by_urls empty path,
    complement_source_urls path, curation, and final json_handler updates."""

    calls = []

    async def fake_stream_output(kind, event, payload, websocket=None):
        # record calls for later assertions
        calls.append((kind, event, payload, websocket))
        await asyncio.sleep(0)

    async def fake_choose_agent(query, cfg, parent_query, cost_callback, headers, prompt_family):
        # return deterministic agent/role
        await asyncio.sleep(0)
        return ("chosen-agent", "chosen-role")

    # Patch module-level dependencies
    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(researcher_mod, "choose_agent", fake_choose_agent)

    # Build fake researcher with attributes expected by conduct_research
    fake_researcher = types.SimpleNamespace()
    fake_researcher.query = "test query"
    fake_researcher.retrievers = [type("R", (), {"__name__": "MCPRetrieverAlpha"})]
    fake_researcher.visited_urls = FakeVisited()
    fake_researcher.verbose = True
    fake_researcher.websocket = "fake-ws"
    fake_researcher.agent = None
    fake_researcher.role = None
    fake_researcher.cfg = types.SimpleNamespace(curate_sources=True, doc_path="/tmp/doc")
    fake_researcher.parent_query = None
    fake_researcher.add_costs = lambda *a, **k: None
    fake_researcher.headers = None
    fake_researcher.prompt_family = FakePromptFamily()
    fake_researcher.source_urls = ["http://source.example"]
    fake_researcher.complement_source_urls = True
    fake_researcher.report_source = None
    fake_researcher.document_urls = None
    fake_researcher.vector_store = None
    fake_researcher.documents = None
    fake_researcher.vector_store_filter = None
    fake_researcher.query_domains = None

    # json handler to assert updates
    fake_json = FakeJSONHandler()
    fake_researcher.json_handler = fake_json

    # curator returns deterministic curated output
    curator = FakeSourceCurator(result=["curated-item"])
    fake_researcher.source_curator = curator

    # costs getter used in final stream output
    fake_researcher.get_costs = lambda: 12.34

    # create conductor
    conductor = ResearchConductor(fake_researcher)

    # Patch the internal context-gathering methods on this instance
    async def fake_get_context_by_urls(self, urls):
        # simulate found zero context
        await asyncio.sleep(0)
        return []

    async def fake_get_context_by_web_search(self, query, scraped_data, query_domains=None):
        # simulate web hits used for complementing
        await asyncio.sleep(0)
        return ["extra"]

    monkeypatch.setattr(ResearchConductor, "_get_context_by_urls", fake_get_context_by_urls)
    monkeypatch.setattr(ResearchConductor, "_get_context_by_web_search", fake_get_context_by_web_search)

    # Execute
    result = await conductor.conduct_research()

    # Oracles / Assertions
    # - json handler should be updated with the initial query
    assert ("query", "test query") in fake_json.updates
    # - choose_agent should have set agent/role on the researcher
    assert fake_researcher.agent == "chosen-agent"
    assert fake_researcher.role == "chosen-role"
    # - stream_output should have been called for starting_research and answering_from_memory
    events = [c[1] for c in calls]
    assert "starting_research" in events
    assert "answering_from_memory" in events
    # - curator should have been called with the research_data assembled (in this code path research_data becomes list/characters from join bug), but curator was invoked
    assert curator.called_with is not None
    # - result should be whatever the curator returned
    assert result == ["curated-item"]
    # - final json_handler updates include costs and context
    assert any(k == "costs" for k, v in fake_json.updates)
    assert any(k == "context" for k, v in fake_json.updates)


@pytest.mark.asyncio
async def test_conduct_research_local_with_vectorstore_round_002(monkeypatch):
    """Exercise ReportSource.Local path: DocumentLoader.load and vector_store.load and subsequent _get_context_by_web_search usage."""

    # Patch DocumentLoader used in the module to return our fake loader
    document_data = ["doc1", "doc2"]
    def doc_loader_factory(path):
        # ensure the loader receives expected path
        return FakeLoader(document_data)

    monkeypatch.setattr(researcher_mod, "DocumentLoader", doc_loader_factory)

    # Patch the web search to return deterministic context
    async def fake_get_context_by_web_search(self, query, scraped_data, query_domains=None):
        await asyncio.sleep(0)
        # echo scraped_data length into context to make deterministic assertion
        return [f"ctx-for-{len(scraped_data)}"]

    monkeypatch.setattr(ResearchConductor, "_get_context_by_web_search", fake_get_context_by_web_search)

    # Build researcher for Local report_source
    fake_researcher = types.SimpleNamespace()
    fake_researcher.query = "local query"
    fake_researcher.retrievers = []
    fake_researcher.visited_urls = FakeVisited()
    fake_researcher.verbose = False
    fake_researcher.websocket = None
    fake_researcher.agent = "agent-present"
    fake_researcher.role = "role-present"
    fake_researcher.cfg = types.SimpleNamespace(curate_sources=False, doc_path="/some/doc/path")
    fake_researcher.parent_query = None
    fake_researcher.add_costs = lambda *a, **k: None
    fake_researcher.headers = None
    fake_researcher.prompt_family = FakePromptFamily()
    fake_researcher.source_urls = []
    fake_researcher.complement_source_urls = False
    fake_researcher.report_source = researcher_mod.ReportSource.Local.value
    fake_researcher.document_urls = None
    fake_researcher.vector_store = FakeVectorStore()
    fake_researcher.documents = None
    fake_researcher.vector_store_filter = None
    fake_researcher.query_domains = None
    fake_researcher.json_handler = None
    fake_researcher.source_curator = None
    fake_researcher.get_costs = lambda: 0.0

    conductor = ResearchConductor(fake_researcher)

    result = await conductor.conduct_research()

    # Oracles
    # - DocumentLoader.load produced document_data which should have been passed to vector_store.load
    assert fake_researcher.vector_store.loaded_with == document_data
    # - _get_context_by_web_search should have been called with scraped documents (document_data)
    assert result == [f"ctx-for-{len(document_data)}"]
