# file: gpt_researcher/skills/writer.py:164-193
# asked: {"lines": [166, 167, 168, 169, 170, 171, 174, 175, 176, 177, 178, 179, 180, 181, 182, 185, 186, 187, 188, 189, 190, 193], "branches": [[166, 167], [166, 174], [185, 186], [185, 193]]}
# gained: {"lines": [166, 167, 168, 169, 170, 171, 174, 175, 176, 177, 178, 179, 180, 181, 182, 185, 186, 187, 188, 189, 190, 193], "branches": [[166, 167], [166, 174], [185, 186], [185, 193]]}

import pytest

from gpt_researcher.skills import writer as writer_module
from gpt_researcher.skills.writer import ReportGenerator


class DummyCfg:
    def __init__(self, agent_role=None):
        self.agent_role = agent_role


class DummyResearcher:
    def __init__(
        self,
        verbose,
        query="test-query",
        context="test-context",
        cfg=None,
        role="default-role",
        websocket=None,
        prompt_family="default-family",
        kwargs=None,
        report_type="rt",
        report_source="rs",
        tone="neutral",
        headers=None,
    ):
        self.verbose = verbose
        self.query = query
        self.context = context
        self.cfg = cfg or DummyCfg()
        self.role = role
        self.websocket = websocket
        self.prompt_family = prompt_family
        self.kwargs = kwargs or {}
        self._costs = []
        # attributes expected by ReportGenerator.__init__
        self.report_type = report_type
        self.report_source = report_source
        self.tone = tone
        self.headers = headers or {}

    def add_costs(self, *args, **kwargs):
        # simple recorder for cost callback
        self._costs.append((args, kwargs))


@pytest.mark.asyncio
async def test_write_introduction_verbose_true_calls_streams_and_returns_intro(monkeypatch):
    calls = []

    async def fake_stream_output(*args, **kwargs):
        # record positional args for assertions
        calls.append(("pos", args))
        calls.append(("kw", kwargs))
        return None

    captured = {}

    async def fake_write_report_introduction(**kw):
        # capture all keyword arguments passed in
        captured.update(kw)
        return "INTRODUCTION-TEXT"

    # Patch the functions used inside the writer module
    monkeypatch.setattr(writer_module, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer_module, "write_report_introduction", fake_write_report_introduction)

    # Prepare a researcher with verbose True so both stream_output calls are executed
    cfg = DummyCfg(agent_role=None)  # force fallback to researcher.role
    researcher = DummyResearcher(
        verbose=True,
        query="my-query",
        context="ctx",
        cfg=cfg,
        role="my-role",
        websocket="ws-object",
        prompt_family="pf",
        kwargs={"extra": "value"},
    )

    rg = ReportGenerator(researcher)

    result = await rg.write_introduction()

    # Verify return value is propagated
    assert result == "INTRODUCTION-TEXT"

    # Verify stream_output was called (two stream events -> at least two recorded positional args entries)
    assert len(calls) >= 4

    # Check first stream_output call args
    first_pos_args = calls[0][1]
    assert first_pos_args[0] == "logs"
    assert first_pos_args[1] == "writing_introduction"
    assert "Writing introduction for 'my-query'" in first_pos_args[2]
    assert first_pos_args[3] == "ws-object"

    # Check second stream_output call args (should be the third recorded "pos" entry)
    second_pos_args = calls[2][1]
    assert second_pos_args[0] == "logs"
    assert second_pos_args[1] == "introduction_written"
    assert "Introduction written for 'my-query'" in second_pos_args[2]
    assert second_pos_args[3] == "ws-object"

    # Verify write_report_introduction was called with expected parameters
    assert captured["query"] == "my-query"
    assert captured["context"] == "ctx"
    # agent_role_prompt should fall back to researcher.role because cfg.agent_role is None
    assert captured["agent_role_prompt"] == "my-role"
    assert captured["config"] is cfg
    assert captured["websocket"] == "ws-object"
    assert captured["prompt_family"] == "pf"
    # kwargs were expanded into the call
    assert captured["extra"] == "value"

    # Instead of asserting identity of the bound method (can be implementation-specific),
    # call the cost_callback and ensure it records into the researcher's _costs list.
    cb = captured.get("cost_callback")
    assert callable(cb)
    # call with sample args
    cb("a", 1, key="v")
    assert researcher._costs, "cost callback did not record costs on researcher"
    # verify the recorded entry matches the args we passed through the callback
    recorded_args, recorded_kwargs = researcher._costs[-1]
    assert recorded_args == ("a", 1)
    assert recorded_kwargs == {"key": "v"}


@pytest.mark.asyncio
async def test_write_introduction_not_verbose_no_streams_and_agent_role_used(monkeypatch):
    stream_called = False

    async def fake_stream_output(*args, **kwargs):
        nonlocal stream_called
        stream_called = True
        return None

    captured = {}

    async def fake_write_report_introduction(**kw):
        captured.update(kw)
        return {"intro": "ok"}

    monkeypatch.setattr(writer_module, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer_module, "write_report_introduction", fake_write_report_introduction)

    # Now cfg.agent_role is set, so agent_role_prompt should be cfg.agent_role
    cfg = DummyCfg(agent_role="AGENT-ROLE")
    researcher = DummyResearcher(
        verbose=False,
        query="q2",
        context="ctx2",
        cfg=cfg,
        role="ignored-role",
        websocket=None,
        prompt_family="pf2",
        kwargs={"k1": 123},
    )

    rg = ReportGenerator(researcher)

    result = await rg.write_introduction()

    # Verify return value is propagated
    assert result == {"intro": "ok"}

    # When verbose is False, stream_output should not have been called
    assert stream_called is False

    # Verify write_report_introduction called with cfg.agent_role used
    assert captured["agent_role_prompt"] == "AGENT-ROLE"
    assert captured["query"] == "q2"
    assert captured["context"] == "ctx2"
    assert captured["config"] is cfg
    assert captured["websocket"] is None
    assert captured["prompt_family"] == "pf2"
    assert captured["k1"] == 123
