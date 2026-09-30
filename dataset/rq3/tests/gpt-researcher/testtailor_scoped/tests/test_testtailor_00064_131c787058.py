import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.researcher')
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
        """Ensure json_handler.update_content is called with the query at start of conduct_research"""
        # Build a minimal dummy researcher with only the attributes used by conduct_research
        class DummyResearcher:
            pass

        researcher = DummyResearcher()
        researcher.query = "test query"
        researcher.retrievers = []  # no retrievers needed for this path
        researcher.visited_urls = set()
        researcher.verbose = False  # disable streaming to websocket
        researcher.websocket = None
        researcher.agent = "agent"  # already set to avoid choose_agent call
        researcher.role = "role"
        researcher.parent_query = None
        researcher.add_costs = lambda *args, **kwargs: None
        researcher.headers = {}
        researcher.prompt_family = type("PF", (), {"join_local_web_documents": lambda self, a, b: a + b})
        researcher.query_domains = []
        researcher.source_urls = ["http://example.com"]  # trigger _get_context_by_urls branch
        researcher.complement_source_urls = False
        researcher.report_source = None
        researcher.report_type = None
        researcher.document_urls = None
        researcher.documents = None
        researcher.vector_store = None

        # Minimal cfg with curate_sources attribute referenced later
        class Cfg:
            curate_sources = False
            max_search_results_per_query = 3
            doc_path = None
        researcher.cfg = Cfg()

        # Minimal context manager and scraper_manager if ever used (they won't be, since we patch the method)
        researcher.context_manager = None
        researcher.scraper_manager = None

        # Create the conductor
        conductor = ResearchConductor(researcher)

        # Replace the json_handler with a fake that records calls
        class FakeJsonHandler:
            def __init__(self):
                self.calls = []

            def update_content(self, key, value):
                self.calls.append((key, value))

            def log_event(self, *args, **kwargs):
                # not used in this test but provided for completeness
                pass

        fake_json = FakeJsonHandler()
        conductor.json_handler = fake_json

        # Patch _get_context_by_urls to avoid external calls and return a known context
        async def fake_get_context_by_urls(urls):
            # confirm that we receive the expected URLs
            return "FAKE_CONTEXT_FROM_URLS"

        conductor._get_context_by_urls = fake_get_context_by_urls

        # Run the async conduct_research and verify behavior
        result = asyncio.run(conductor.conduct_research())

        # Assert json_handler.update_content was called with the query at the start
        self.assertTrue(len(fake_json.calls) >= 1)
        self.assertEqual(fake_json.calls[0], ("query", "test query"))

        # Ensure the returned context matches our fake
        self.assertEqual(result, "FAKE_CONTEXT_FROM_URLS")
