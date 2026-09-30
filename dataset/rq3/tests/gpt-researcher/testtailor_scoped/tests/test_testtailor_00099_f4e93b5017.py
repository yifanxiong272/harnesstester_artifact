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
        """Test that stream_output is called when researcher.verbose is True."""
        # build a minimal researcher object with required attributes
        class DummyCfg:
            smart_llm_model = "model"
            smart_llm_provider = "provider"
            llm_kwargs = {}

        class DummyPromptFamily:
            def curate_sources(self, query, source_data, max_results):
                return "curate prompt"

        class DummyResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = "fake_ws"
                self.role = "system_role"
                self.query = "some query"
                self.cfg = DummyCfg()
                self.prompt_family = DummyPromptFamily()
            def add_costs(self, *args, **kwargs):
                pass

        researcher = DummyResearcher()

        # prepare fake async functions to patch into the module where SourceCurator is defined
        calls = []

        async def fake_create_chat_completion(*args, **kwargs):
            # return a JSON string so json.loads in the code returns a list
            return __import__('json').dumps(["https://example.com/source1"])

        async def fake_stream_output(category, name, message, websocket):
            calls.append((category, name, message, websocket))
            return None

        # patch the create_chat_completion and stream_output used by SourceCurator
        module = __import__(SourceCurator.__module__, fromlist=['*'])
        with unittest.mock.patch.object(module, "create_chat_completion", new=fake_create_chat_completion), \
             unittest.mock.patch.object(module, "stream_output", new=fake_stream_output):
            curator = SourceCurator(researcher)
            loop = __import__('asyncio').get_event_loop()
            result = loop.run_until_complete(curator.curate_sources(["src1", "src2"], max_results=1))

        # validate returned curated sources and that stream_output was called for the "evaluating" message
        self.assertEqual(result, ["https://example.com/source1"])
        # ensure at least one stream_output call was made and that it contains the evaluating message
        self.assertTrue(any("Evaluating and curating sources" in call[2] for call in calls))
        # ensure websocket passed through
        self.assertTrue(any(call[3] == researcher.websocket for call in calls))
