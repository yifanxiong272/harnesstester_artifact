# file: gpt_researcher/skills/researcher.py:89-211
# asked: {"lines": [91, 92, 94, 97, 98, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 119, 120, 121, 122, 123, 124, 125, 126, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 143, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 159, 161, 162, 163, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 190, 191, 194, 195, 196, 197, 199, 200, 201, 202, 203, 204, 206, 207, 208, 210, 211], "branches": [[91, 92], [91, 94], [104, 105], [104, 119], [119, 120], [119, 130], [131, 132], [131, 135], [135, 136], [135, 149], [138, 139], [138, 145], [145, 146], [145, 194], [149, 150], [149, 152], [152, 153], [152, 161], [156, 157], [156, 159], [161, 162], [161, 171], [162, 163], [162, 165], [166, 167], [166, 168], [171, 172], [171, 181], [181, 182], [181, 190], [185, 186], [185, 187], [190, 191], [190, 194], [195, 196], [195, 199], [199, 200], [199, 210], [206, 207], [206, 210]]}
# gained: {"lines": [91, 92, 94, 97, 98, 101, 102, 104, 105, 106, 107, 108, 109, 111, 112, 113, 114, 115, 119, 120, 121, 122, 123, 124, 125, 126, 130, 131, 135, 136, 137, 138, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 159, 161, 162, 163, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 190, 191, 194, 195, 196, 197, 199, 200, 201, 202, 203, 204, 206, 207, 208, 210, 211], "branches": [[91, 92], [104, 105], [104, 119], [119, 120], [131, 135], [135, 136], [135, 149], [138, 145], [145, 146], [149, 150], [149, 152], [152, 153], [152, 161], [156, 157], [161, 162], [161, 171], [162, 163], [162, 165], [166, 167], [171, 172], [171, 181], [181, 182], [181, 190], [185, 186], [190, 191], [195, 196], [195, 199], [199, 200], [199, 210], [206, 207]]}

import os
import sys
import types
import asyncio
import pytest

import gpt_researcher.skills.researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor
from gpt_researcher.utils.enum import ReportSource


class DummyJSONHandler:
    def __init__(self):
        self.updated = {}

    def update_content(self, key, value):
        self.updated[key] = value


class DummyCfg:
    def __init__(self, doc_path=None, curate_sources=False):
        self.doc_path = doc_path
        self.curate_sources = curate_sources


class DummyVectorStore:
    def __init__(self):
        self.loaded = None

    def load(self, data):
        self.loaded = data


class DummyPromptFamily:
    def join_local_web_documents(self, docs_context, web_context):
        return f"joined:{docs_context}|{web_context}"


class DummySourceCurator:
    def __init__(self, curated=None):
        self.curated = curated or ["cur1"]

    async def curate_sources(self, research_data):
        # Return something different to ensure it's used
        return self.curated


class DummyResearcher:
    def __init__(self):
        self.query = "test query"
        self.retrievers = []
        self.visited_urls = set(["already"])
        self.verbose = False
        self.websocket = None
        self.agent = None
        self.role = None
        self.cfg = DummyCfg(doc_path="/tmp")
        self.parent_query = None
        self.add_costs = lambda *a, **k: None
        self.headers = {}
        self.prompt_family = DummyPromptFamily()
        self.source_urls = []
        self.complement_source_urls = False
        self.query_domains = None
        self.report_source = None
        self.vector_store = None
        self.document_urls = []
        self.documents = []
        self.vector_store_filter = None
        self.source_curator = DummySourceCurator()
        self._costs = 0.0
        self.context = None

    def get_costs(self):
        return self._costs


@pytest.mark.asyncio
async def test_conduct_research_with_source_urls_and_complement(monkeypatch):
    """
    Test branch where source_urls are provided and complement_source_urls is True.
    Also test verbose path, choose_agent invocation, json_handler updates, and finalization.
    """
    # Prepare researcher
    r = DummyResearcher()
    r.source_urls = ["http://example.com"]
    r.complement_source_urls = True
    r.verbose = True
    # Add a retriever with name not indicating MCP
    def retr(): pass
    retr.__name__ = "SimpleRetriever"
    r.retrievers = [retr]

    # track choose_agent called
    choose_called = {"called": False}

    async def fake_choose_agent(**kwargs):
        choose_called["called"] = True
        return "agent_x", "role_y"

    async def fake_stream_output(*args, **kwargs):
        # simply no-op async
        return None

    async def fake_get_context_by_urls(urls):
        # return a list so complement branch appends to it
        return ["doc_from_url"]

    async def fake_get_context_by_web_search(query, scraped_data, query_domains=None):
        # return list of small strings; join will be used to create a string
        return ["a", "b"]

    # Monkeypatch module-level functions used in conduct_research
    monkeypatch.setattr(researcher_mod, "choose_agent", fake_choose_agent)
    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Monkeypatch instance methods on ResearchConductor
    monkeypatch.setattr(ResearchConductor, "_get_context_by_urls", lambda self, urls: fake_get_context_by_urls(urls))
    monkeypatch.setattr(ResearchConductor, "_get_context_by_web_search", lambda self, q, s, d=None: fake_get_context_by_web_search(q, s, d))

    conductor = ResearchConductor(r)
    # Override json handler to capture updates
    dummy_json = DummyJSONHandler()
    conductor.json_handler = dummy_json

    # run
    ctx = await conductor.conduct_research()

    # Assertions: choose_agent was used, json handler updated, context is set on researcher and returned
    assert choose_called["called"] is True, "choose_agent should have been called"
    assert "query" in dummy_json.updated and dummy_json.updated["query"] == "test query"
    assert conductor.researcher.context == ctx
    # ensure visited_urls was cleared (original had "already")
    assert conductor.researcher.visited_urls == set(), "visited_urls should be cleared at start"
    # final log leads to context being stringifiable: ensure it's not None
    assert ctx is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("report_source", [
    ReportSource.Web.value,
    ReportSource.Local.value,
    ReportSource.Hybrid.value,
    ReportSource.Azure.value,
    ReportSource.LangChainDocuments.value,
    ReportSource.LangChainVectorStore.value,
])
async def test_conduct_research_report_source_branches(monkeypatch, tmp_path, report_source):
    """
    Parameterized test to exercise the different report_source branches:
    Web, Local, Hybrid (both online and local), Azure, LangChainDocuments, LangChainVectorStore.
    """
    # Prepare researcher
    r = DummyResearcher()
    r.source_urls = []  # ensure we go through report_source dispatch
    r.report_source = report_source
    r.query_domains = ["example.com"]

    # Common monkeypatches for functions
    async def fake_get_context_by_web_search(query, scraped_data, query_domains=None):
        return f"web_context_for:{query}"

    async def fake_get_context_by_vectorstore(query, filter=None):
        return f"vector_context_for:{query}"

    monkeypatch.setattr(ResearchConductor, "_get_context_by_web_search", lambda self, q, s, d=None: fake_get_context_by_web_search(q, s, d))
    monkeypatch.setattr(ResearchConductor, "_get_context_by_vectorstore", lambda self, q, f=None: fake_get_context_by_vectorstore(q, f))

    # Replace module-level DocumentLoader, OnlineDocumentLoader, LangChainDocumentLoader
    class DL:
        def __init__(self, path_or_list):
            self.path_or_list = path_or_list

        async def load(self):
            # Return pretend documents list
            return ["docA", "docB"]

    class OnlineDL:
        def __init__(self, urls):
            self.urls = urls

        async def load(self):
            return ["online_doc1"]

    class LCLoader:
        def __init__(self, documents):
            self.documents = documents

        async def load(self):
            return ["lc_doc1"]

    # Monkeypatch module references to DocumentLoader etc.
    monkeypatch.setattr(researcher_mod, "DocumentLoader", DL)
    monkeypatch.setattr(researcher_mod, "OnlineDocumentLoader", OnlineDL)
    monkeypatch.setattr(researcher_mod, "LangChainDocumentLoader", LCLoader)

    # For Azure branch we must provide the module that will be imported relatively
    if report_source == ReportSource.Azure.value:
        # create a fake module at the expected package path: gpt_researcher.document.azure_document_loader
        azure_mod_name = "gpt_researcher.document.azure_document_loader"
        azure_mod = types.ModuleType(azure_mod_name)
        class AzureLoader:
            def __init__(self, container_name=None, connection_string=None):
                self.container_name = container_name
                self.connection_string = connection_string

            async def load(self):
                # return list of files (paths) expected by DocumentLoader below
                return ["azure_file1", "azure_file2"]

        azure_mod.AzureDocumentLoader = AzureLoader
        sys.modules[azure_mod_name] = azure_mod
        # Ensure environment variables exist (code uses os.getenv)
        monkeypatch.setenv("AZURE_CONTAINER_NAME", "dummy_container")
        monkeypatch.setenv("AZURE_CONNECTION_STRING", "dummy_connection")

    # Vector store behavior test for branches that use it
    if report_source in (ReportSource.Local.value, ReportSource.Hybrid.value, ReportSource.LangChainDocuments.value):
        vs = DummyVectorStore()
        r.vector_store = vs
    else:
        r.vector_store = None

    # Hybrid specific: test both with document_urls present and absent
    if report_source == ReportSource.Hybrid.value:
        # First test: with document_urls present -> OnlineDocumentLoader branch
        r.document_urls = ["http://docsource"]
        conductor = ResearchConductor(r)
        # override json handler to avoid None usage
        conductor.json_handler = DummyJSONHandler()
        result1 = await conductor.conduct_research()
        # check that vector_store loaded if present
        if r.vector_store:
            assert r.vector_store.loaded is not None
        assert isinstance(result1, str) or result1 is not None

        # Now test: without document_urls -> DocumentLoader branch
        r2 = DummyResearcher()
        r2.source_urls = []
        r2.report_source = ReportSource.Hybrid.value
        r2.vector_store = DummyVectorStore()
        r2.document_urls = []
        r2.cfg = DummyCfg(doc_path=str(tmp_path))
        conductor2 = ResearchConductor(r2)
        conductor2.json_handler = DummyJSONHandler()
        result2 = await conductor2.conduct_research()
        # should have vector_store loaded
        assert r2.vector_store.loaded is not None
        assert result2 is not None
        return  # hybrid handled; exit test

    # LangChainVectorStore branch: ensure _get_context_by_vectorstore used
    if report_source == ReportSource.LangChainVectorStore.value:
        conductor = ResearchConductor(r)
        conductor.json_handler = DummyJSONHandler()
        res = await conductor.conduct_research()
        assert res == f"vector_context_for:{r.query}"
        return

    # LangChainDocuments branch
    if report_source == ReportSource.LangChainDocuments.value:
        # Provide some langchain documents in researcher.documents
        r.documents = ["lc_doc"]
        conductor = ResearchConductor(r)
        conductor.json_handler = DummyJSONHandler()
        res = await conductor.conduct_research()
        # vector_store should have been loaded
        if r.vector_store:
            assert r.vector_store.loaded is not None
        assert "web_context_for" in str(res)
        return

    # Local branch
    if report_source == ReportSource.Local.value:
        conductor = ResearchConductor(r)
        conductor.json_handler = DummyJSONHandler()
        res = await conductor.conduct_research()
        # DocumentLoader.load should have returned list of length 2 -> logged; ensure vector store loaded
        if r.vector_store:
            assert r.vector_store.loaded == ["docA", "docB"]
        assert "web_context_for" in str(res)
        return

    # Azure branch
    if report_source == ReportSource.Azure.value:
        conductor = ResearchConductor(r)
        conductor.json_handler = DummyJSONHandler()
        res = await conductor.conduct_research()
        # After Azure, DocumentLoader was called with azure files and web search used; ensure non-empty
        assert res is not None
        return

    # Web branch (fallback)
    if report_source == ReportSource.Web.value:
        conductor = ResearchConductor(r)
        conductor.json_handler = DummyJSONHandler()
        res = await conductor.conduct_research()
        assert res == f"web_context_for:{r.query}"


@pytest.mark.asyncio
async def test_curation_and_json_updates(monkeypatch):
    """
    Test the curate_sources True path and ensure json_handler is updated with costs and context
    when verbose is True.
    """
    r = DummyResearcher()
    r.source_urls = []
    r.report_source = ReportSource.Web.value
    r.cfg = DummyCfg(doc_path="/tmp", curate_sources=True)
    # Simulate a source_curator that returns something distinct
    r.source_curator = DummySourceCurator(curated=["curated_one", "curated_two"])
    r.verbose = True
    r._costs = 12.34

    async def fake_get_context_by_web_search(query, scraped_data, query_domains=None):
        # return a list-like object to be curated
        return ["raw1", "raw2"]

    monkeypatch.setattr(ResearchConductor, "_get_context_by_web_search", lambda self, q, s, d=None: fake_get_context_by_web_search(q, s, d))

    conductor = ResearchConductor(r)
    dummy_json = DummyJSONHandler()
    conductor.json_handler = dummy_json

    # monkeypatch stream_output to avoid external effects
    async def fake_stream_output(*args, **kwargs):
        return None

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    ctx = await conductor.conduct_research()

    # After curation, researcher.context should be curated list
    assert conductor.researcher.context == ["curated_one", "curated_two"]
    # json handler should have costs and context keys updated
    assert "costs" in dummy_json.updated
    assert dummy_json.updated["costs"] == r.get_costs()
    assert "context" in dummy_json.updated
    assert dummy_json.updated["context"] == conductor.researcher.context
