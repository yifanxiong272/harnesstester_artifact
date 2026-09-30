import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.mcp.retriever')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Initialize MCPRetriever and verify attributes and component initialization calls."""
        # Prepare a dummy researcher with mcp_configs and cfg
        class DummyResearcher:
            pass

        researcher = DummyResearcher()
        researcher.mcp_configs = [{"name": "mcp1", "url": "http://example"}]
        researcher.cfg = {"llm": "dummy"}

        # Get the module where MCPRetriever is defined without using sys
        module = __import__(MCPRetriever.__module__, fromlist=["*"])

        # Save original module-level classes to restore later
        orig_client_mgr = getattr(module, "MCPClientManager", None)
        orig_tool_selector = getattr(module, "MCPToolSelector", None)
        orig_research_skill = getattr(module, "MCPResearchSkill", None)
        orig_streamer_cls = getattr(module, "MCPStreamer", None)

        # Create mock classes and instances
        client_mgr_mock_cls = unittest.mock.MagicMock(name="MCPClientManager")
        client_mgr_instance = unittest.mock.MagicMock(name="client_manager_instance")
        client_mgr_mock_cls.return_value = client_mgr_instance

        tool_selector_mock_cls = unittest.mock.MagicMock(name="MCPToolSelector")
        tool_selector_instance = unittest.mock.MagicMock(name="tool_selector_instance")
        tool_selector_mock_cls.return_value = tool_selector_instance

        research_skill_mock_cls = unittest.mock.MagicMock(name="MCPResearchSkill")
        research_skill_instance = unittest.mock.MagicMock(name="research_skill_instance")
        research_skill_mock_cls.return_value = research_skill_instance

        streamer_mock_cls = unittest.mock.MagicMock(name="MCPStreamer")
        streamer_instance = unittest.mock.MagicMock(name="streamer_instance")
        # Ensure streamer has stream_log_sync method
        streamer_instance.stream_log_sync = unittest.mock.MagicMock(name="stream_log_sync")
        streamer_instance.stream_error = unittest.mock.MagicMock(name="stream_error")
        streamer_instance.stream_stage_start = unittest.mock.MagicMock(name="stream_stage_start")
        streamer_instance.stream_warning = unittest.mock.MagicMock(name="stream_warning")
        streamer_instance.stream_log = unittest.mock.MagicMock(name="stream_log")
        streamer_instance.stream_research_results = unittest.mock.MagicMock(name="stream_research_results")
        streamer_mock_cls.return_value = streamer_instance

        # Patch the module-level classes
        setattr(module, "MCPClientManager", client_mgr_mock_cls)
        setattr(module, "MCPToolSelector", tool_selector_mock_cls)
        setattr(module, "MCPResearchSkill", research_skill_mock_cls)
        setattr(module, "MCPStreamer", streamer_mock_cls)

        try:
            # Instantiate the retriever
            retriever = MCPRetriever(
                query="test-query",
                headers={"Authorization": "token"},
                query_domains=["example.com"],
                websocket="fake-websocket",
                researcher=researcher
            )

            # Verify basic attributes
            self.assertEqual(retriever.query, "test-query")
            self.assertEqual(retriever.headers, {"Authorization": "token"})
            self.assertEqual(retriever.query_domains, ["example.com"])
            self.assertEqual(retriever.websocket, "fake-websocket")
            self.assertIs(retriever.researcher, researcher)

            # Verify mcp_configs and cfg were fetched from researcher
            self.assertEqual(retriever.mcp_configs, researcher.mcp_configs)
            self.assertEqual(retriever.cfg, researcher.cfg)

            # Verify component constructors were called with correct arguments
            client_mgr_mock_cls.assert_called_once_with(researcher.mcp_configs)
            tool_selector_mock_cls.assert_called_once_with(researcher.cfg, researcher)
            research_skill_mock_cls.assert_called_once_with(researcher.cfg, researcher)
            streamer_mock_cls.assert_called_once_with("fake-websocket")

            # _all_tools_cache should be initialized to None
            self.assertIsNone(retriever._all_tools_cache)

            # Verify streamer logged initialization messages (at least two calls)
            calls = streamer_instance.stream_log_sync.call_args_list
            self.assertGreaterEqual(len(calls), 2)
            messages = [call.args[0] for call in calls if call.args]
            # Check that expected substrings are present in the logged messages
            self.assertTrue(any("Initializing MCP retriever for query: test-query" in m for m in messages))
            self.assertTrue(any("Found 1 MCP server configurations" in m for m in messages))

        finally:
            # Restore original classes to avoid side effects on other tests
            if orig_client_mgr is not None:
                setattr(module, "MCPClientManager", orig_client_mgr)
            else:
                if hasattr(module, "MCPClientManager"):
                    delattr(module, "MCPClientManager")

            if orig_tool_selector is not None:
                setattr(module, "MCPToolSelector", orig_tool_selector)
            else:
                if hasattr(module, "MCPToolSelector"):
                    delattr(module, "MCPToolSelector")

            if orig_research_skill is not None:
                setattr(module, "MCPResearchSkill", orig_research_skill)
            else:
                if hasattr(module, "MCPResearchSkill"):
                    delattr(module, "MCPResearchSkill")

            if orig_streamer_cls is not None:
                setattr(module, "MCPStreamer", orig_streamer_cls)
            else:
                if hasattr(module, "MCPStreamer"):
                    delattr(module, "MCPStreamer")
