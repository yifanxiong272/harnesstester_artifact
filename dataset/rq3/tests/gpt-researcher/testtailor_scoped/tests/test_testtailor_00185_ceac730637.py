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
        """Ensure verbose research emits starting_research and agent_generated stream outputs."""
        calls = []

        # Async stub to capture stream_output calls
        async def dummy_stream_output(*args, **kwargs):
            calls.append({"args": args, "kwargs": kwargs})

        # Patch stream_output in the ResearchConductor's module
        mod = __import__(ResearchConductor.__module__, fromlist=['*'])
        original_stream_output = getattr(mod, "stream_output", None)
        setattr(mod, "stream_output", dummy_stream_output)

        try:
            # Minimal researcher stub with attributes used by conduct_research up to the target point
            class DummyRetriever:
                pass

            class ResearcherStub:
                def __init__(self):
                    self.query = "example query"
                    self.websocket = object()
                    self.agent = "TestAgent"
                    self.role = "TestRole"
                    self.retrievers = [DummyRetriever]
                    self.visited_urls = set()
                    self.verbose = True
                    # Minimal config used later
                    self.cfg = type("C", (), {"curate_sources": False, "max_search_results_per_query": 5})
                    self.parent_query = None
                    self.headers = {}
                    self.prompt_family = type("PF", (), {"join_local_web_documents": lambda a, b, c: ""})
                    self.query_domains = []
                    # Ensure attributes referenced elsewhere exist
                    self.source_urls = []
                    self.complement_source_urls = False
                    self.report_source = None
                    self.report_type = None
                def add_costs(self, *a, **k):
                    pass
                def add_research_sources(self, *a, **k):
                    pass
                def get_costs(self):
                    return 0.0

            researcher = ResearcherStub()
            conductor = ResearchConductor(researcher)
            # Avoid json handler interactions in tests
            conductor.json_handler = None

            # Run the async conduct_research
            loop = __import__('asyncio').get_event_loop()
            loop.run_until_complete(conductor.conduct_research())

            # Verify that the first two stream_output calls correspond to the targeted events
            self.assertGreaterEqual(len(calls), 2, "Expected at least two stream_output calls")
            first_call = calls[0]["args"]
            second_call = calls[1]["args"]

            # Check event keys and that messages contain expected content
            self.assertEqual(first_call[1], "starting_research")
            self.assertIn("Starting the research task", first_call[2])

            self.assertEqual(second_call[1], "agent_generated")
            self.assertEqual(second_call[2], researcher.agent)

        finally:
            # Restore original stream_output to avoid side effects
            setattr(mod, "stream_output", original_stream_output)
