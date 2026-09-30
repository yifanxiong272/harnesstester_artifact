import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.detailed_report.detailed_report')
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
        """Instantiate DetailedReport and verify GPTResearcher is constructed with expected params,
        MCP params are propagated, headers default to {}, research_id format, and max_search_results override applied.
        """
        import importlib
        import sys

        # Try several possible module paths to locate DetailedReport implementation
        candidate_modules = (
            "backend.report_type.detailed_report.detailed_report",
            "backend.report_type.detailed_report",
            "report_type.detailed_report",
            "report_type",
        )

        detailed_mod = None
        for mod_name in candidate_modules:
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            if hasattr(mod, "DetailedReport"):
                detailed_mod = mod
                break

        self.assertIsNotNone(detailed_mod, f"Could not find DetailedReport in any of {candidate_modules}")

        # Create a dummy GPTResearcher to avoid external dependencies (OpenAI, etc.)
        class DummyCFG:
            def __init__(self):
                self.max_search_results_per_query = 5

        class DummyGPTResearcher:
            last_init_kwargs = None

            def __init__(self, **kwargs):
                DummyGPTResearcher.last_init_kwargs = kwargs
                self.cfg = DummyCFG()
                self.visited_urls = set()
                self.context = []
                # propagate MCP attributes to mimic real researcher
                self.mcp_configs = kwargs.get("mcp_configs")
                self.mcp_strategy = kwargs.get("mcp_strategy")
                self.agent = None
                self.role = None

            # minimal stubs for attributes/methods potentially accessed elsewhere
            def __getattr__(self, item):
                if item in ("extract_headers", "extract_sections", "table_of_contents", "add_references"):
                    return lambda *a, **k: "" if item != "extract_headers" else []
                raise AttributeError

        # Patch the DetailedReport module's GPTResearcher reference to our dummy
        original_gpt = getattr(detailed_mod, "GPTResearcher", None)
        setattr(detailed_mod, "GPTResearcher", DummyGPTResearcher)

        try:
            # Instantiate DetailedReport with MCP params and max_search_results to hit the target branches
            dr = detailed_mod.DetailedReport(
                query="test query",
                report_type="detailed_report",
                report_source="web",
                source_urls=["https://example.com"],
                document_urls=["doc1"],
                query_domains=["example.com"],
                config_path="config/path",
                tone="neutral",
                websocket=object(),
                subtopics=[],
                headers=None,  # should default to {}
                complement_source_urls=True,
                mcp_configs={"mode": "fast"},
                mcp_strategy="round_robin",
                max_search_results=42,
            )

            # Check headers defaulted to {}
            self.assertEqual(dr.headers, {})

            # Check research_id format starts with expected prefix
            self.assertTrue(hasattr(dr, "research_id"))
            self.assertTrue(str(dr.research_id).startswith("detailed_"))

            # Verify GPTResearcher was initialized and received the MCP params
            init_kwargs = DummyGPTResearcher.last_init_kwargs
            self.assertIsNotNone(init_kwargs)
            # report_type should be overridden to "research_report" inside constructor params
            self.assertEqual(init_kwargs.get("report_type"), "research_report")
            self.assertEqual(init_kwargs.get("query"), "test query")
            self.assertEqual(init_kwargs.get("report_source"), "web")
            self.assertEqual(init_kwargs.get("mcp_configs"), {"mode": "fast"})
            self.assertEqual(init_kwargs.get("mcp_strategy"), "round_robin")

            # Ensure max_search_results override applied to the gpt_researcher.cfg
            self.assertEqual(dr.gpt_researcher.cfg.max_search_results_per_query, 42)
        finally:
            # Restore original GPTResearcher if present
            if original_gpt is not None:
                setattr(detailed_mod, "GPTResearcher", original_gpt)
