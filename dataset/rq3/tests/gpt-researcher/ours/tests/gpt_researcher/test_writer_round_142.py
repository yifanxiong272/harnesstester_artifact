import pytest
import asyncio
from types import SimpleNamespace
from gpt_researcher.skills import writer


class DummyCfg:
    def __init__(self, agent_role=None):
        self.agent_role = agent_role


class ResearcherStub:
    def __init__(self, *, verbose, query, websocket=None, cfg=None, role="default-role", prompt_family="family", kwargs=None):
        self.verbose = verbose
        self.query = query
        self.websocket = websocket
        self.cfg = cfg or DummyCfg()
        self.role = role
        self.prompt_family = prompt_family
        self.kwargs = kwargs or {}
        self._costs = []

    def add_costs(self, cost):
        # simple deterministic cost recorder
        self._costs.append(cost)


@pytest.mark.asyncio
async def test_verbose_true_round_142(monkeypatch):
    """
    When researcher.verbose is True, stream_output should be called twice (before and after),
    and write_conclusion should be awaited and its return forwarded.
    """
    calls = []
    write_calls = []

    async def fake_stream_output(channel, event, message, websocket):
        # record ordered calls with their payloads
        calls.append((channel, event, message, websocket))

    async def fake_write_conclusion(**kwargs):
        # capture provided kwargs and return a deterministic conclusion
        write_calls.append(kwargs)
        return "CONCLUSION_FROM_FAKE"

    monkeypatch.setattr(writer, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer, "write_conclusion", fake_write_conclusion)

    researcher = ResearcherStub(verbose=True, query="test-query", websocket="wss://dummy", role="my-role")

    inst = object.__new__(writer.ReportGenerator)
    inst.researcher = researcher

    result = await inst.write_report_conclusion("report content")

    # oracle: returned conclusion is the fake return value
    assert result == "CONCLUSION_FROM_FAKE"

    # stream_output should have been called twice in order
    assert len(calls) == 2, "expected two stream_output calls when verbose is True"

    # first call is the writing_conclusion event and mentions the query
    ch0, ev0, msg0, ws0 = calls[0]
    assert ch0 == "logs"
    assert ev0 == "writing_conclusion"
    assert "Writing conclusion" in msg0 or "Writing conclusion" in msg0.encode('utf-8').decode('utf-8')
    assert "test-query" in msg0
    assert ws0 == "wss://dummy"

    # second call is the conclusion_written event and mentions the query
    ch1, ev1, msg1, ws1 = calls[1]
    assert ch1 == "logs"
    assert ev1 == "conclusion_written"
    assert "Conclusion written" in msg1
    assert "test-query" in msg1
    assert ws1 == "wss://dummy"

    # write_conclusion should have been called exactly once with agent_role_prompt from researcher.role
    assert len(write_calls) == 1
    wc_kwargs = write_calls[0]
    assert wc_kwargs.get("query") == "test-query"
    assert wc_kwargs.get("context") == "report content"
    assert wc_kwargs.get("config") == researcher.cfg
    # since cfg.agent_role is None by default, agent_role_prompt should fall back to researcher.role
    assert wc_kwargs.get("agent_role_prompt") == "my-role"
    assert wc_kwargs.get("websocket") == "wss://dummy"
    assert wc_kwargs.get("prompt_family") == researcher.prompt_family


@pytest.mark.asyncio
async def test_verbose_false_uses_cfg_agent_role_round_142(monkeypatch):
    """
    When researcher.verbose is False, stream_output should not be called,
    and agent_role_prompt should be taken from cfg.agent_role when present.
    """
    calls = []
    write_calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    async def fake_write_conclusion(**kwargs):
        write_calls.append(kwargs)
        return "CONCLUSION_CFG"

    monkeypatch.setattr(writer, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer, "write_conclusion", fake_write_conclusion)

    cfg = DummyCfg(agent_role="configured-role")
    researcher = ResearcherStub(verbose=False, query="q2", websocket=None, cfg=cfg, role="ignored-role")

    inst = object.__new__(writer.ReportGenerator)
    inst.researcher = researcher

    result = await inst.write_report_conclusion("ctx")

    # oracle: returned conclusion from fake_write_conclusion
    assert result == "CONCLUSION_CFG"

    # stream_output should not have been called at all when verbose is False
    assert calls == []

    # write_conclusion must have been called and receive agent_role_prompt from cfg.agent_role
    assert len(write_calls) == 1
    wc_kwargs = write_calls[0]
    assert wc_kwargs.get("agent_role_prompt") == "configured-role"
    assert wc_kwargs.get("query") == "q2"
    assert wc_kwargs.get("context") == "ctx"
    # ensure cost callback is present and callable
    assert callable(wc_kwargs.get("cost_callback"))
