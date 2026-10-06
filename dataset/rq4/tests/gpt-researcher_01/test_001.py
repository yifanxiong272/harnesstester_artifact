import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from gpt_researcher.skills.researcher import ResearchConductor

@pytest.mark.asyncio
async def test_probe_001():
    # Deterministic initial and additional contexts
    initial = [{"url": "u1", "content": "c1"}]
    additional = ["alpha", "beta"]

    # Minimal researcher with attributes required by conduct_research
    researcher = SimpleNamespace(
        query="test-query",
        source_urls=["http://example.com"],
        complement_source_urls=True,
        agent="agent-x",
        role="role-y",
        retrievers=[type("R", (), {})],
        cfg=SimpleNamespace(curate_sources=False),
        verbose=False,
        websocket=None,
        query_domains=[],
        parent_query=None,
        headers={},
        prompt_family=None,
        add_costs=lambda *a, **k: None,
        get_costs=lambda: 0,
    )

    conductor = ResearchConductor(researcher)

    # Override the async retrieval helpers deterministically
    conductor._get_context_by_urls = AsyncMock(return_value=list(initial))
    conductor._get_context_by_web_search = AsyncMock(return_value=list(additional))

    # Exercise the public entrypoint
    result = await conductor.conduct_research()

    # Primary behavioral oracle: element-wise list concatenation must preserve items
    assert isinstance(result, list), f"expected list result, got {type(result)!r}"
    assert len(result) == len(initial) + len(additional), (
        f"expected length {len(initial) + len(additional)}, got {len(result)}"
    )
    assert result[-len(additional):] == additional, (
        f"expected trailing elements {additional!r}, got {result[-len(additional):]!r}"
    )
