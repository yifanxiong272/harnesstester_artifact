# file: gpt_researcher/retrievers/mcp/retriever.py:44-89
# asked: {"lines": [44, 46, 47, 48, 49, 50, 64, 65, 66, 67, 68, 71, 72, 75, 76, 77, 78, 81, 84, 85, 86, 88, 89], "branches": [[84, 85], [84, 88]]}
# gained: {"lines": [44, 47, 48, 49, 50, 64, 65, 66, 67, 68, 71, 72, 75, 76, 77, 78, 81, 84, 85, 86, 88, 89], "branches": [[84, 85], [84, 88]]}

import pytest

from types import SimpleNamespace

MODULE_PATH = "gpt_researcher.retrievers.mcp.retriever"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    # Prevent any accidental network I/O by ensuring no real clients are used.
    # This fixture can be expanded if needed.
    yield


def _patch_core_components(monkeypatch, module, *, manager_cls=None, tool_selector_cls=None,
                           research_cls=None, streamer_cls=None):
    # Provide defaults if not supplied
    manager_cls = manager_cls or (lambda configs: SimpleNamespace(configs=configs))
    tool_selector_cls = tool_selector_cls or (lambda cfg, researcher: SimpleNamespace(cfg=cfg, researcher=researcher))
    research_cls = research_cls or (lambda cfg, researcher: SimpleNamespace(cfg=cfg, researcher=researcher))

    monkeypatch.setattr(module, "MCPClientManager", manager_cls)
    monkeypatch.setattr(module, "MCPToolSelector", tool_selector_cls)
    monkeypatch.setattr(module, "MCPResearchSkill", research_cls)
    # Streamer replacement should be a class taking websocket and exposing stream_log_sync
    if streamer_cls is None:
        class DefaultStreamer:
            def __init__(self, websocket):
                self.websocket = websocket
                self.logs = []

            def stream_log_sync(self, msg):
                self.logs.append(msg)

        streamer_cls = DefaultStreamer

    monkeypatch.setattr(module, "MCPStreamer", streamer_cls)
    return manager_cls, tool_selector_cls, research_cls, streamer_cls


def test_init_with_configs(monkeypatch):
    # Import module and class under test
    module = pytest.importorskip(MODULE_PATH)
    MCPRetriever = module.MCPRetriever

    # Prepare fake components and patch them into the module
    class FakeManager:
        def __init__(self, configs):
            self.configs = configs

    class FakeToolSelector:
        def __init__(self, cfg, researcher):
            self.cfg = cfg
            self.researcher = researcher

    class FakeResearchSkill:
        def __init__(self, cfg, researcher):
            self.cfg = cfg
            self.researcher = researcher

    class FakeStreamer:
        def __init__(self, websocket):
            self.websocket = websocket
            self.logs = []

        def stream_log_sync(self, msg):
            self.logs.append(msg)

    _patch_core_components(
        monkeypatch,
        module,
        manager_cls=FakeManager,
        tool_selector_cls=FakeToolSelector,
        research_cls=FakeResearchSkill,
        streamer_cls=FakeStreamer,
    )

    # Monkeypatch MCPRetriever._get_mcp_configs and _get_config to control behavior
    test_configs = [{"url": "http://example.com", "name": "ex"}]
    test_cfg = {"llm": "gpt-test"}

    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: test_configs)
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: test_cfg)

    # Call constructor with explicit params
    query = "test query"
    headers = {"Authorization": "token"}
    domains = ["example.com"]
    ws = object()
    researcher = object()

    retriever = MCPRetriever(query=query, headers=headers, query_domains=domains, websocket=ws, researcher=researcher)

    # Verify attributes set correctly
    assert retriever.query == query
    assert retriever.headers == headers
    assert retriever.query_domains == domains
    assert retriever.websocket is ws
    assert retriever.researcher is researcher

    # Verify internal components were constructed with expected args
    assert isinstance(retriever.client_manager, FakeManager)
    assert retriever.client_manager.configs is test_configs

    assert isinstance(retriever.tool_selector, FakeToolSelector)
    assert retriever.tool_selector.cfg is test_cfg
    assert retriever.tool_selector.researcher is researcher

    assert isinstance(retriever.mcp_researcher, FakeResearchSkill)
    assert retriever.mcp_researcher.cfg is test_cfg
    assert retriever.mcp_researcher.researcher is researcher

    # Streamer should be our FakeStreamer and have two initialization logs
    assert isinstance(retriever.streamer, FakeStreamer)
    # Two expected messages when configs are present
    expected_msg_1 = f"🔧 Initializing MCP retriever for query: {query}"
    expected_msg_2 = f"🔧 Found {len(test_configs)} MCP server configurations"
    assert retriever.streamer.logs == [expected_msg_1, expected_msg_2]

    # Cache should be initialized but empty
    assert retriever._all_tools_cache is None


def test_init_without_configs_logs_error_and_critical_stream(monkeypatch):
    # Import module and class under test
    module = pytest.importorskip(MODULE_PATH)
    MCPRetriever = module.MCPRetriever

    # Patch core components to avoid side effects
    class FakeManager:
        def __init__(self, configs):
            self.configs = configs

    class FakeToolSelector:
        def __init__(self, cfg, researcher):
            self.cfg = cfg
            self.researcher = researcher

    class FakeResearchSkill:
        def __init__(self, cfg, researcher):
            self.cfg = cfg
            self.researcher = researcher

    class FakeStreamer:
        def __init__(self, websocket):
            self.websocket = websocket
            self.logs = []

        def stream_log_sync(self, msg):
            self.logs.append(msg)

    _patch_core_components(
        monkeypatch,
        module,
        manager_cls=FakeManager,
        tool_selector_cls=FakeToolSelector,
        research_cls=FakeResearchSkill,
        streamer_cls=FakeStreamer,
    )

    # Force _get_mcp_configs to return empty list and override _get_config as well
    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [])
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {"cfg": "val"})

    # Capture logger.error calls
    logger_calls = []

    def fake_logger_error(msg, *args, **kwargs):
        logger_calls.append((msg, args, kwargs))

    # Patch the module's logger.error
    if hasattr(module, "logger"):
        monkeypatch.setattr(module.logger, "error", fake_logger_error)
    else:
        # If no logger attr, create one on module
        monkeypatch.setattr(module, "logger", SimpleNamespace(error=fake_logger_error))

    # Instantiate retriever with no configs
    retriever = MCPRetriever(query="q2", headers=None, query_domains=None, websocket=None, researcher=None)

    # Verify client manager created with empty configs
    assert isinstance(retriever.client_manager, FakeManager)
    assert retriever.client_manager.configs == []

    # Logger.error should have been called once with an explanatory message
    assert len(logger_calls) == 1
    assert "No MCP server configurations found" in logger_calls[0][0]

    # Streamer should have received the critical message in logs
    assert isinstance(retriever.streamer, FakeStreamer)
    assert retriever.streamer.logs == [
        "❌ CRITICAL: No MCP server configurations found. Please check documentation."
    ]
