import pytest
from types import SimpleNamespace

from gpt_researcher.skills.researcher import ResearchConductor

@pytest.mark.asyncio
async def test_probe_001_preserve_joined_websearch_as_single_element():
    # Build a minimal researcher to activate the source_urls branch and request complement_search
    researcher = SimpleNamespace(
        query="test query",
        retrievers=[type("R", (), {"__name__": "R"})],
        verbose=False,  # avoid stream_output side effects
        websocket=None,
        agent="agent",  # satisfy choose_agent guard
        role="role",
        source_urls=["http://example.com/doc"],  # non-empty to take the source-URLs branch
        complement_source_urls=True,  # request additional web search
        report_source=None,
        cfg=SimpleNamespace(curate_sources=False),  # avoid downstream curation path
        vector_store=None,
        query_domains=[],
        parent_query=None,
        headers={},
        prompt_family=SimpleNamespace(join_local_web_documents=lambda a, b: None),
    )

    conductor = ResearchConductor(researcher)

    # Stub the I/O helpers used in the targeted branch
    async def _fake_get_context_by_urls(urls):
        # return a list so research_data is a list and the list+string concatenation path is exercised
        return ["docA"]

    async def _fake_get_context_by_web_search(query, docs, domains=None):
        # deterministic short pieces that will be joined into 'x y'
        return ["x", "y"]

    conductor._get_context_by_urls = _fake_get_context_by_urls
    conductor._get_context_by_web_search = _fake_get_context_by_web_search

    # Run the entrypoint under test
    out = await conductor.conduct_research()

    # Independent oracle: the web-search contribution must appear as the joined string 'x y'
    joined = " ".join(["x", "y"])  # 'x y'
    ctx = researcher.context

    assert ctx == joined or (isinstance(ctx, list) and joined in ctx), (
        f"Web-search contribution was not preserved as a single element; observed context: {ctx!r}"
    )
