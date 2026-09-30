import pytest
from types import SimpleNamespace

import gpt_researcher.skills.writer as writer_module
from gpt_researcher.skills.writer import ReportGenerator

@pytest.mark.asyncio
async def test_get_draft_section_titles_verbose_true_round_145(monkeypatch):
    # Capture calls
    gen_called = {}
    stream_calls = []

    async def fake_generate_draft_section_titles(**kwargs):
        # record the exact kwargs passed for inspection
        gen_called.update(kwargs)
        return ["Title 1", "Title 2"]

    async def fake_stream_output(*args, **kwargs):
        stream_calls.append((args, kwargs))
        return None

    # Patch the names where the writer module resolves them
    monkeypatch.setattr(writer_module, "generate_draft_section_titles", fake_generate_draft_section_titles)
    monkeypatch.setattr(writer_module, "stream_output", fake_stream_output)

    # Prepare a minimal researcher object matching the expected shape
    class Cfg:
        def __init__(self, agent_role=None):
            self.agent_role = agent_role

    researcher = SimpleNamespace()
    researcher.verbose = True
    researcher.query = "test-query"
    researcher.websocket = "fake-ws"
    researcher.context = {"k": "v"}
    researcher.cfg = Cfg(agent_role=None)  # test fallback to researcher.role
    researcher.role = "fallback-role"
    researcher.add_costs = lambda *a, **k: None
    researcher.prompt_family = "pf"
    researcher.kwargs = {}
    # Attributes required by ReportGenerator.__init__
    researcher.report_type = "standard"
    researcher.report_source = "source-a"
    researcher.tone = "neutral"
    researcher.headers = {"h": "v"}

    rg = ReportGenerator(researcher)

    result = await rg.get_draft_section_titles("current-sub")

    # Assertions: return value, that generate was awaited and stream_output called twice
    assert result == ["Title 1", "Title 2"]

    # verify generate_draft_section_titles received expected keys and values
    assert gen_called["query"] == researcher.query
    assert gen_called["current_subtopic"] == "current-sub"
    assert gen_called["context"] is researcher.context
    # since cfg.agent_role is None, role should be researcher.role
    assert gen_called["role"] == "fallback-role"
    assert gen_called["websocket"] == researcher.websocket
    assert gen_called["config"] is researcher.cfg
    assert gen_called["cost_callback"] is researcher.add_costs
    assert gen_called["prompt_family"] == researcher.prompt_family

    # verify stream_output was called before and after generation by checking two calls
    assert len(stream_calls) == 2
    # check the event names (second positional arg in each call)
    assert stream_calls[0][0][1] == "generating_draft_sections"
    assert stream_calls[1][0][1] == "draft_sections_generated"
    # websocket was forwarded as last positional arg in calls
    assert stream_calls[0][0][-1] == researcher.websocket
    assert stream_calls[1][0][-1] == researcher.websocket


@pytest.mark.asyncio
async def test_get_draft_section_titles_verbose_false_with_agent_role_round_145(monkeypatch):
    # Capture calls
    gen_called = {}
    stream_calls = []

    async def fake_generate_draft_section_titles(**kwargs):
        gen_called.update(kwargs)
        return ["Only Title"]

    async def fake_stream_output(*args, **kwargs):
        stream_calls.append((args, kwargs))
        return None

    monkeypatch.setattr(writer_module, "generate_draft_section_titles", fake_generate_draft_section_titles)
    monkeypatch.setattr(writer_module, "stream_output", fake_stream_output)

    class Cfg:
        def __init__(self, agent_role=None):
            self.agent_role = agent_role

    researcher = SimpleNamespace()
    researcher.verbose = False
    researcher.query = "another-query"
    researcher.websocket = None
    researcher.context = {"ctx": 123}
    researcher.cfg = Cfg(agent_role="explicit-agent-role")
    researcher.role = "should-not-be-used"
    researcher.add_costs = lambda *a, **k: None
    researcher.prompt_family = "pf2"
    researcher.kwargs = {"extra": "value"}
    # Attributes required by ReportGenerator.__init__
    researcher.report_type = "detailed"
    researcher.report_source = "source-b"
    researcher.tone = "formal"
    researcher.headers = {}

    rg = ReportGenerator(researcher)

    result = await rg.get_draft_section_titles("sub-2")

    # When verbose is False, stream_output should not be called
    assert result == ["Only Title"]
    assert len(stream_calls) == 0

    # verify generate_draft_section_titles received the explicit agent role from cfg
    assert gen_called["role"] == "explicit-agent-role"
    assert gen_called["query"] == researcher.query
    assert gen_called["current_subtopic"] == "sub-2"
    # verify kwargs were forwarded into the call
    assert gen_called.get("extra") == "value"
