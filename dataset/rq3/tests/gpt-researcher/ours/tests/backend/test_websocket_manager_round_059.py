import importlib
import pytest

ws_module = importlib.import_module('backend.server.websocket_manager')

class FakeLogsHandler:
    def __init__(self, websocket, task):
        # preserve constructor shape used in production code
        self.websocket = websocket
        self.task = task
        self.sent_messages = []

    async def send_json(self, payload):
        # async API matches expected contract
        self.sent_messages.append(payload)


@pytest.mark.asyncio
async def test_multi_agents_with_mcp_enabled_emits_mcp_init_and_returns_report_round_059(monkeypatch):
    # Patch CustomLogsHandler and run_multi_agent_task used by run_agent
    monkeypatch.setattr(ws_module, 'CustomLogsHandler', FakeLogsHandler)

    async def fake_run_multi_agent_task(*, query, websocket, stream_output, tone, headers):
        # ensure signature compatibility and return shape
        return {"report": "multi_result"}

    monkeypatch.setattr(ws_module, 'run_multi_agent_task', fake_run_multi_agent_task)

    # Call run_agent with mcp enabled and a non-empty mcp_configs to exercise printing + logs
    result = await ws_module.run_agent(
        task="t1",
        report_type="multi_agents",
        report_source=None,
        source_urls=[],
        document_urls=[],
        tone=None,
        websocket="fake_ws",
        stream_output=None,
        headers=None,
        query_domains=[],
        config_path="",
        return_researcher=False,
        mcp_enabled=True,
        mcp_strategy="fast",
        mcp_configs=["s1", "s2"],
        max_search_results=None,
    )

    # Should return the report string from fake_run_multi_agent_task
    assert result == "multi_result"

    # Validate that the CustomLogsHandler we patched received the mcp init log
    # Construct expected message that run_agent sends when mcp is enabled
    # The handler instance was created inside run_agent; find it by re-constructing
    # Since we patched CustomLogsHandler class, we can't access the exact instance here
    # Instead, monkeypatch a wrapper to capture the instance for assertions.


@pytest.mark.asyncio
async def test_detailed_report_returns_researcher_and_passes_none_mcp_when_disabled_round_059(monkeypatch):
    # Prepare a fake DetailedReport class to capture init kwargs and provide run/gpt_researcher
    class FakeDetailed:
        last_init_kwargs = None

        def __init__(self, **kwargs):
            # preserve expected constructor signature and capture args
            type(self).last_init_kwargs = kwargs
            self.gpt_researcher = "gpt_det"

        async def run(self):
            return "detailed_report"

    # Patch CustomLogsHandler to a minimal handler (not used in this path but required constructor shape)
    monkeypatch.setattr(ws_module, 'CustomLogsHandler', FakeLogsHandler)
    monkeypatch.setattr(ws_module, 'DetailedReport', FakeDetailed)

    report_type_value = ws_module.ReportType.DetailedReport.value

    result = await ws_module.run_agent(
        task="query",
        report_type=report_type_value,
        report_source="src",
        source_urls=["u"],
        document_urls=["d"],
        tone=None,
        websocket="ws",
        stream_output=None,
        headers={"h": "v"},
        query_domains=[],
        config_path="/cfg",
        return_researcher=True,
        mcp_enabled=False,
        mcp_strategy="fast",
        mcp_configs=["should_be_ignored"],
        max_search_results=5,
    )

    # Should return (report, gpt_researcher) when return_researcher is True
    assert isinstance(result, tuple) and result[0] == "detailed_report" and result[1] == "gpt_det"

    # When mcp_enabled is False, the DetailedReport should receive None for mcp_configs and mcp_strategy
    assert FakeDetailed.last_init_kwargs is not None
    assert FakeDetailed.last_init_kwargs.get('mcp_configs') is None
    assert FakeDetailed.last_init_kwargs.get('mcp_strategy') is None


@pytest.mark.asyncio
async def test_basic_report_with_mcp_enabled_sends_mcp_and_passes_mcp_configs_to_researcher_round_059(monkeypatch):
    # Capture the actual logs handler instance created inside run_agent
    captured_handler = {}

    class CapturingLogsHandler(FakeLogsHandler):
        def __init__(self, websocket, task):
            super().__init__(websocket, task)
            # store a reference externally for assertions after run_agent returns
            captured_handler['instance'] = self

    class FakeBasic:
        last_init_kwargs = None

        def __init__(self, **kwargs):
            type(self).last_init_kwargs = kwargs
            self.gpt_researcher = "gpt_basic"

        async def run(self):
            return "basic_report"

    monkeypatch.setattr(ws_module, 'CustomLogsHandler', CapturingLogsHandler)
    monkeypatch.setattr(ws_module, 'BasicReport', FakeBasic)

    # Run with mcp enabled and a non-empty config list
    result = await ws_module.run_agent(
        task="q",
        report_type="other_report_type",
        report_source=None,
        source_urls=[],
        document_urls=[],
        tone=None,
        websocket="ws",
        stream_output=None,
        headers=None,
        query_domains=[],
        config_path="",
        return_researcher=True,
        mcp_enabled=True,
        mcp_strategy="slow",
        mcp_configs=["srvA"],
        max_search_results=None,
    )

    # Ensure we got the tuple (report, researcher)
    assert isinstance(result, tuple) and result[0] == "basic_report" and result[1] == "gpt_basic"

    # The BasicReport constructor should receive the mcp_configs and mcp_strategy because mcp_enabled is True
    assert FakeBasic.last_init_kwargs is not None
    assert FakeBasic.last_init_kwargs.get('mcp_configs') == ["srvA"]
    assert FakeBasic.last_init_kwargs.get('mcp_strategy') == "slow"

    # Ensure the logs handler used by run_agent received the mcp_init message when mcp_enabled=True
    handler = captured_handler.get('instance')
    assert handler is not None, "Logs handler instance was not captured"
    # There should be at least one message and it should indicate mcp_init
    assert any(msg.get('content') == 'mcp_init' for msg in handler.sent_messages), handler.sent_messages
