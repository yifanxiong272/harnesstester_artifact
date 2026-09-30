# file: gpt_researcher/skills/writer.py:164-193
# asked: {"lines": [166, 167, 168, 169, 170, 171, 174, 175, 176, 177, 178, 179, 180, 181, 182, 185, 186, 187, 188, 189, 190, 193], "branches": [[166, 167], [166, 174], [185, 186], [185, 193]]}
# gained: {"lines": [166, 167, 168, 169, 170, 171, 174, 175, 176, 177, 178, 179, 180, 181, 182, 185, 186, 187, 188, 189, 190, 193], "branches": [[166, 167], [166, 174], [185, 186], [185, 193]]}

import pytest
from types import SimpleNamespace
import asyncio

@pytest.mark.asyncio
async def test_write_introduction_verbose_with_agent_role(monkeypatch):
    # Import ReportGenerator from correct module path
    from gpt_researcher.skills.writer import ReportGenerator

    stream_calls = []
    write_calls = []

    async def fake_stream_output(stream_type, event, message, websocket):
        stream_calls.append((stream_type, event, message, websocket))
        await asyncio.sleep(0)

    async def fake_write_report_introduction(**kwargs):
        write_calls.append(kwargs.copy())
        await asyncio.sleep(0)
        return {"introduction": "generated-intro", "meta": {"called": True}}

    # Patch the names imported in the writer module
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.stream_output",
        fake_stream_output,
    )
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.write_report_introduction",
        fake_write_report_introduction,
    )

    websocket = object()
    cfg = SimpleNamespace(agent_role="agent-role", some_other_cfg="cfgval")
    researcher = SimpleNamespace(
        verbose=True,
        query="test-query",
        websocket=websocket,
        context="test-context",
        cfg=cfg,
        role="ignored-role",
        add_costs=lambda *a, **k: None,
        prompt_family="family-A",
        kwargs={"extra": "value"},
        # attributes required by ReportGenerator.__init__
        report_type="type-A",
        report_source="source-A",
        tone="neutral",
        headers=["H1", "H2"],
    )

    rg = ReportGenerator(researcher)

    result = await rg.write_introduction()

    assert result == {"introduction": "generated-intro", "meta": {"called": True}}
    assert len(write_calls) == 1
    called_kwargs = write_calls[0]
    assert called_kwargs["query"] == "test-query"
    assert called_kwargs["context"] == "test-context"
    assert called_kwargs["agent_role_prompt"] == "agent-role"
    assert called_kwargs["config"] is cfg
    assert called_kwargs["websocket"] is websocket
    assert called_kwargs["cost_callback"] is researcher.add_costs
    assert called_kwargs["prompt_family"] == "family-A"
    assert called_kwargs["extra"] == "value"

    assert len(stream_calls) == 2
    first = stream_calls[0]
    second = stream_calls[1]
    assert first[0] == "logs"
    assert first[1] == "writing_introduction"
    assert "Writing introduction for 'test-query'" in first[2]
    assert first[3] is websocket

    assert second[0] == "logs"
    assert second[1] == "introduction_written"
    assert "Introduction written for 'test-query'" in second[2]
    assert second[3] is websocket


@pytest.mark.asyncio
async def test_write_introduction_nonverbose_uses_role_when_agent_role_missing(monkeypatch):
    from gpt_researcher.skills.writer import ReportGenerator

    stream_calls = []
    write_calls = []

    async def fake_stream_output(*args, **kwargs):
        stream_calls.append((args, kwargs))
        await asyncio.sleep(0)

    async def fake_write_report_introduction(**kwargs):
        write_calls.append(kwargs.copy())
        await asyncio.sleep(0)
        return "plain-intro"

    monkeypatch.setattr(
        "gpt_researcher.skills.writer.stream_output",
        fake_stream_output,
    )
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.write_report_introduction",
        fake_write_report_introduction,
    )

    websocket = object()
    cfg = SimpleNamespace(agent_role=None)
    researcher = SimpleNamespace(
        verbose=False,
        query="another-query",
        websocket=websocket,
        context={"k": "v"},
        cfg=cfg,
        role="fallback-role",
        add_costs=lambda *a, **k: None,
        prompt_family="family-B",
        kwargs={},
        # attributes required by ReportGenerator.__init__
        report_type="type-B",
        report_source="source-B",
        tone="formal",
        headers=[],
    )

    rg = ReportGenerator(researcher)

    result = await rg.write_introduction()

    assert result == "plain-intro"
    assert len(stream_calls) == 0
    assert len(write_calls) == 1
    called_kwargs = write_calls[0]
    assert called_kwargs["agent_role_prompt"] == "fallback-role"
    assert called_kwargs["query"] == "another-query"
    assert called_kwargs["context"] == {"k": "v"}
    assert called_kwargs["config"] is cfg
    assert called_kwargs["websocket"] is websocket
    assert called_kwargs["prompt_family"] == "family-B"
