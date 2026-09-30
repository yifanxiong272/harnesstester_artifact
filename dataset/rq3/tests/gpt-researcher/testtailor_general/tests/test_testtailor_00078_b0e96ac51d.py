import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.curator')
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
        """Ensure curate_sources prints initial summary and returns parsed LLM output
        and calls stream_output when verbose is True."""
        # local imports
        asyncio = __import__("asyncio")
        json = __import__("json")
        import inspect

        # Prepare fake async helpers to patch into the SourceCurator's module namespace
        stream_calls = []

        async def fake_stream_output(channel, stage, message, websocket):
            stream_calls.append((channel, stage, message, websocket))

        async def fake_create_chat_completion(*args, **kwargs):
            # return a JSON string that json.loads will parse into a list
            return json.dumps(["https://example.com/source1", "https://example.com/source2"])

        # Patch the functions on the module where SourceCurator is defined
        module_name = SourceCurator.__module__
        module = __import__(module_name, fromlist=["*"])
        setattr(module, "create_chat_completion", fake_create_chat_completion)
        setattr(module, "stream_output", fake_stream_output)

        # Build a minimal researcher stub with required attributes
        class DummyPromptFamily:
            def curate_sources(self, query, source_data, max_results):
                return "Evaluate these sources for relevance and credibility."

        class DummyCfg:
            def __init__(self):
                self.smart_llm_model = "fake-model"
                self.smart_llm_provider = "fake-provider"
                self.llm_kwargs = {}

        class DummyResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = None
                self.role = "system role"
                self.prompt_family = DummyPromptFamily()
                self.query = "test query"
                self.cfg = DummyCfg()
            def add_costs(self, *args, **kwargs):
                # no-op cost callback
                pass

        researcher = DummyResearcher()
        curator = SourceCurator(researcher)

        # Prepare source data and run the async method
        source_data = ["http://a.example", "http://b.example"]
        result = asyncio.run(curator.curate_sources(source_data, max_results=2))

        # Verify that the returned value matches the fake LLM output parsed as JSON
        self.assertEqual(result, ["https://example.com/source1", "https://example.com/source2"])

        # Because verbose=True, stream_output should have been called at least once
        self.assertTrue(len(stream_calls) >= 1)
