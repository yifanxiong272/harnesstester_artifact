import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.basic_report.basic_report')
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
        """Instantiate BasicReport and verify initialization and GPTResearcher params without calling real GPTResearcher."""
        import importlib
        import sys

        # Try to find a module that exposes BasicReport
        candidate_module_names = (
            "backend.report_type.basic_report.basic_report",
            "backend.report_type",
            "report_type",
            "backend.report_type.basic_report",
        )
        basic_report_cls = None
        defining_module = None
        for name in candidate_module_names:
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            if hasattr(mod, "BasicReport"):
                basic_report_cls = getattr(mod, "BasicReport")
                break

        if basic_report_cls is None:
            # As a last resort, search loaded modules for BasicReport
            for mod in list(sys.modules.values()):
                if mod is None:
                    continue
                if hasattr(mod, "BasicReport"):
                    basic_report_cls = getattr(mod, "BasicReport")
                    break

        if basic_report_cls is None:
            self.skipTest("Could not locate BasicReport class")

        # Ensure we patch the module that actually defines BasicReport
        def_mod = importlib.import_module(basic_report_cls.__module__)

        # Prepare a fake GPTResearcher to avoid external dependencies (like OpenAI)
        class FakeGPTResearcher:
            def __init__(self, **kwargs):
                # capture init kwargs for assertions
                self.kwargs = kwargs
                class Cfg:
                    pass
                self.cfg = Cfg()
                # default value before override
                self.cfg.max_search_results_per_query = 10

            async def conduct_research(self):
                return None

            async def write_report(self):
                return "fake-report"

        # Patch the defining module so BasicReport will construct our fake researcher
        setattr(def_mod, "GPTResearcher", FakeGPTResearcher)

        # Prepare inputs
        query = "find cats"
        query_domains = ["example.com"]
        report_type = "typeA"
        report_source = "web"
        source_urls = ["https://example.com"]
        document_urls = ["doc1"]
        tone = "Objective"
        config_path = "conf/path"
        websocket = object()
        headers = None
        mcp_configs = {"k": "v"}
        mcp_strategy = "round_robin"
        max_search_results = 5

        # Instantiate BasicReport (this should use FakeGPTResearcher)
        br = basic_report_cls(
            query=query,
            query_domains=query_domains,
            report_type=report_type,
            report_source=report_source,
            source_urls=source_urls,
            document_urls=document_urls,
            tone=tone,
            config_path=config_path,
            websocket=websocket,
            headers=headers,
            mcp_configs=mcp_configs,
            mcp_strategy=mcp_strategy,
            max_search_results=max_search_results,
        )

        # Basic attribute assignments
        self.assertEqual(br.query, query)
        self.assertEqual(br.query_domains, query_domains)
        self.assertEqual(br.report_type, report_type)
        self.assertEqual(br.report_source, report_source)
        self.assertEqual(br.source_urls, source_urls)
        self.assertEqual(br.document_urls, document_urls)
        self.assertEqual(br.tone, tone)
        self.assertEqual(br.config_path, config_path)
        # headers default when None should be dict
        self.assertEqual(br.headers, {})

        # research_id generated
        self.assertIsInstance(br.research_id, str)
        self.assertTrue(br.research_id.startswith("research_"))

        # GPTResearcher was constructed with expected params (our fake)
        self.assertIsInstance(br.gpt_researcher, FakeGPTResearcher)
        gw_kwargs = br.gpt_researcher.kwargs
        self.assertEqual(gw_kwargs["query"], query)
        self.assertEqual(gw_kwargs["query_domains"], query_domains)
        self.assertEqual(gw_kwargs["report_type"], report_type)
        self.assertEqual(gw_kwargs["report_source"], report_source)
        self.assertEqual(gw_kwargs["source_urls"], source_urls)
        self.assertEqual(gw_kwargs["document_urls"], document_urls)
        self.assertEqual(gw_kwargs["tone"], tone)
        self.assertEqual(gw_kwargs["config_path"], config_path)
        self.assertEqual(gw_kwargs["websocket"], websocket)
        self.assertEqual(gw_kwargs["headers"], {})

        # MCP params should be forwarded
        self.assertEqual(gw_kwargs["mcp_configs"], mcp_configs)
        self.assertEqual(gw_kwargs["mcp_strategy"], mcp_strategy)

        # max_search_results should override the cfg value
        self.assertEqual(br.gpt_researcher.cfg.max_search_results_per_query, int(max_search_results))
