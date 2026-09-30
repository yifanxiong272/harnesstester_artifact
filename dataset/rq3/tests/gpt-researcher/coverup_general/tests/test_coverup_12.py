# file: backend/server/websocket_manager.py:116-183
# asked: {"lines": [119, 125, 126, 127, 128, 129, 130, 134, 135, 136, 137, 138, 139, 140, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 178, 180, 181, 183], "branches": [[125, 126], [125, 134], [134, 135], [134, 144], [144, 145], [144, 163], [180, 181], [180, 183]]}
# gained: {"lines": [119, 125, 126, 127, 128, 129, 130, 134, 135, 136, 137, 138, 139, 140, 142, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 160, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 178, 180, 181, 183], "branches": [[125, 126], [125, 134], [134, 135], [134, 144], [144, 145], [144, 163], [180, 181], [180, 183]]}

import importlib
import pytest
import asyncio

def _import_websocket_manager():
    """Try multiple possible import paths for the websocket_manager module used in different repo layouts."""
    candidates = [
        "gpt_researcher.backend.server.websocket_manager",
        "backend.server.websocket_manager",
        "gpt_researcher.backend.websocket_manager",
        "backend.websocket_manager",
        "websocket_manager",
    ]
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    pytest.skip("Could not import websocket_manager from any known path; skipping tests.")


@pytest.mark.asyncio
async def test_run_agent_multi_agents_with_mcp(monkeypatch):
    ws = _import_websocket_manager()

    # Fake logs handler that records send_json calls and stores init args
    class FakeLogsHandler:
        def __init__(self, websocket, task):
            self.websocket = websocket
            self.task = task
            self.sent = []

        async def send_json(self, payload):
            self.sent.append(payload)

    # Replace CustomLogsHandler with our fake (use raising=False for safety)
    monkeypatch.setattr(ws, "CustomLogsHandler", FakeLogsHandler, raising=False)

    # Create a fake run_multi_agent_task that asserts websocket is the logs handler
    async def fake_run_multi_agent_task(query, websocket, stream_output, tone, headers):
        assert isinstance(websocket, FakeLogsHandler)
        assert query == "task-multi"
        return {"report": "multi_agent_report"}

    monkeypatch.setattr(ws, "run_multi_agent_task", fake_run_multi_agent_task, raising=False)

    dummy_ws = object()

    result = await ws.run_agent(
        "task-multi",
        "multi_agents",
        "report_source",
        ["http://a"],
        ["doc1"],
        None,
        dummy_ws,
        stream_output=None,
        headers={"h": "v"},
        query_domains=[],
        config_path="",
        return_researcher=False,
        mcp_enabled=True,
        mcp_strategy="fast",
        mcp_configs=["server1", "server2"],
        max_search_results=None,
    )

    assert result == "multi_agent_report"

    # Now capture the created handler to verify send_json payload
    created_handler = None

    def capture_CustomLogsHandler(websocket, task):
        nonlocal created_handler
        created_handler = FakeLogsHandler(websocket, task)
        return created_handler

    monkeypatch.setattr(ws, "CustomLogsHandler", capture_CustomLogsHandler, raising=False)

    result2 = await ws.run_agent(
        "task-multi",
        "multi_agents",
        "report_source",
        [],
        [],
        None,
        dummy_ws,
        stream_output=None,
        headers=None,
        return_researcher=False,
        mcp_enabled=True,
        mcp_strategy="fast",
        mcp_configs=["s1"],
    )

    assert result2 == "multi_agent_report"
    assert created_handler is not None
    assert len(created_handler.sent) >= 1
    payload = created_handler.sent[0]
    assert payload.get("type") == "logs"
    assert payload.get("content") == "mcp_init"
    out = payload.get("output", "")
    # Should mention strategy and server count
    assert "fast" in out
    assert "1" in out or "server" in out  # ensure servers count or word "server" present


@pytest.mark.asyncio
async def test_run_agent_detailed_and_return_researcher(monkeypatch):
    ws = _import_websocket_manager()

    # Fake logs handler
    class FakeLogsHandler:
        def __init__(self, websocket, task):
            self.websocket = websocket
            self.task = task

        async def send_json(self, payload):
            pass

    monkeypatch.setattr(ws, "CustomLogsHandler", FakeLogsHandler, raising=False)

    # Fake DetailedReport that records init kwargs and returns a known report from run()
    class FakeDetailedReport:
        def __init__(self, query, query_domains, report_type, report_source, source_urls,
                     document_urls, tone, config_path, websocket, headers,
                     mcp_configs, mcp_strategy, max_search_results):
            assert isinstance(websocket, FakeLogsHandler)
            self.query = query
            self.gpt_researcher = "detailed_gpt_researcher"

        async def run(self):
            return "detailed_report_result"

    monkeypatch.setattr(ws, "DetailedReport", FakeDetailedReport, raising=False)

    # Determine the DetailedReport value; fallback to a known string if not present
    try:
        detailed_value = ws.ReportType.DetailedReport.value
    except Exception:
        detailed_value = "detailed_report"

    result = await ws.run_agent(
        "task-detailed",
        detailed_value,
        "rs",
        ["su1"],
        ["du1"],
        None,
        object(),
        headers={"h": "v"},
        return_researcher=True,
        mcp_enabled=False,
    )

    assert isinstance(result, tuple)
    report, researcher_obj = result
    assert report == "detailed_report_result"
    assert researcher_obj == "detailed_gpt_researcher"


@pytest.mark.asyncio
async def test_run_agent_basic_report_returns_report(monkeypatch):
    ws = _import_websocket_manager()

    class FakeLogsHandler:
        def __init__(self, websocket, task):
            self.websocket = websocket
            self.task = task

        async def send_json(self, payload):
            pass

    monkeypatch.setattr(ws, "CustomLogsHandler", FakeLogsHandler, raising=False)

    class FakeBasicReport:
        def __init__(self, query, query_domains, report_type, report_source, source_urls,
                     document_urls, tone, config_path, websocket, headers,
                     mcp_configs, mcp_strategy, max_search_results):
            assert isinstance(websocket, FakeLogsHandler)
            # When mcp_enabled False, mcp_configs should be None
            assert mcp_configs is None
            self.gpt_researcher = "basic_gpt_researcher"

        async def run(self):
            return "basic_report_result"

    monkeypatch.setattr(ws, "BasicReport", FakeBasicReport, raising=False)

    result = await ws.run_agent(
        "task-basic",
        "some_other_type",
        "rs",
        [],
        [],
        None,
        object(),
        headers=None,
        return_researcher=False,
        mcp_enabled=False,
    )

    assert result == "basic_report_result"
