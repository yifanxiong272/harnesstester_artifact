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
        """Ensure MCPRetriever logs a critical error and streams a critical message when no mcp_configs provided."""
        # Minimal researcher with empty mcp_configs and a cfg attribute
        researcher = type("R", (), {"cfg": object(), "mcp_configs": []})()

        # Access the globals where MCPRetriever.__init__ is defined
        globals_map = MCPRetriever.__init__.__globals__

        # Save originals to restore later
        keys_to_patch = [
            "MCPStreamer",
            "MCPClientManager",
            "MCPToolSelector",
            "MCPResearchSkill",
            "logger",
        ]
        originals = {k: globals_map.get(k) for k in keys_to_patch}

        # Create lightweight fakes to avoid side effects
        class FakeClientManager:
            def __init__(self, configs):
                self.configs = configs

            async def close_client(self):
                return None

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
                # capture sync logs
                self.logs.append(msg)

            async def stream_stage_start(self, *a, **k): pass
            async def stream_log(self, *a, **k): pass
            async def stream_warning(self, *a, **k): pass
            async def stream_error(self, *a, **k): pass
            async def stream_research_results(self, *a, **k): pass

        class FakeLogger:
            def __init__(self):
                self.error_calls = []

            def error(self, *args, **kwargs):
                # Record calls for assertions
                self.error_calls.append((args, kwargs))

            def info(self, *a, **k): pass
            def debug(self, *a, **k): pass

        fake_logger = FakeLogger()

        # Patch the globals to use fakes
        try:
            globals_map["MCPClientManager"] = FakeClientManager
            globals_map["MCPToolSelector"] = FakeToolSelector
            globals_map["MCPResearchSkill"] = FakeResearchSkill
            globals_map["MCPStreamer"] = FakeStreamer
            globals_map["logger"] = fake_logger

            # Instantiate the retriever; __init__ should hit the branch for no mcp_configs
            retriever = MCPRetriever(query="test query", researcher=researcher)

            # Verify internal state reflects no configs
            self.assertEqual(retriever.mcp_configs, [])

            # Ensure the fake streamer was used and received the critical message
            self.assertIsInstance(retriever.streamer, FakeStreamer)
            critical_messages = [m for m in retriever.streamer.logs if "CRITICAL" in m or "No MCP server configurations" in m]
            self.assertTrue(critical_messages, "Expected a critical stream log when no mcp_configs provided")

            # Ensure logger.error was called with the expected substring
            self.assertTrue(fake_logger.error_calls, "Expected logger.error to be called")
            # Check that at least one error call contained the expected text
            self.assertTrue(
                any("No MCP server configurations" in str(args) or "No MCP server configurations" in str(kwargs)
                    for args, kwargs in [(a, kw) for (a, kw) in fake_logger.error_calls]),
                "Expected 'No MCP server configurations' in logger.error calls"
            )

        finally:
            # Restore original globals
            for k, v in originals.items():
                if v is None:
                    globals_map.pop(k, None)
                else:
                    globals_map[k] = v
