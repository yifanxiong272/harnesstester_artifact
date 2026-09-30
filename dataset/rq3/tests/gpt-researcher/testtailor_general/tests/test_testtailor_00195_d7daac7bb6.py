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
        """Ensure MCPRetriever logs an error and continues when no mcp_configs are provided."""
        # Create a minimal researcher with cfg but no mcp_configs to trigger the target branch
        class DummyCfg:
            pass

        class DummyResearcher:
            def __init__(self):
                self.cfg = DummyCfg()
                self.mcp_configs = []  # <- This should trigger the "no configs" branch

        researcher = DummyResearcher()

        # Capture error logs emitted during initialization
        with self.assertLogs(MCPRetriever.__module__, level="ERROR") as cm:
            retriever = MCPRetriever(query="test query", researcher=researcher)

        # Verify that mcp_configs was set to an empty list and streamer was created
        self.assertEqual(retriever.mcp_configs, [])
        self.assertIsNotNone(retriever.streamer)

        # Ensure the expected error message was logged during initialization
        self.assertTrue(
            any("No MCP server configurations found. The retriever will fail during search." in msg for msg in cm.output),
            "Expected critical error log not found when mcp_configs is empty"
        )

        # Calling search should not raise and should return an empty list (graceful handling)
        results = retriever.search()
        self.assertEqual(results, [])
