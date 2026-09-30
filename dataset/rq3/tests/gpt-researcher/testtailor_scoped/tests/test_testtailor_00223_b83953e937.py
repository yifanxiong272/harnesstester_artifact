import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.query_processing')
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
        """Ensure generate_search_queries_prompt is called with cfg.max_iterations and
        that the function returns the parsed list from the LLM response.
        """
        # Prepare a fake prompt family that records the call
        called = {}

        class FakePromptFamily:
            def generate_search_queries_prompt(self, query, parent_query, report_type, max_iterations, context):
                called['args'] = {
                    'query': query,
                    'parent_query': parent_query,
                    'report_type': report_type,
                    'max_iterations': max_iterations,
                    'context': context,
                }
                return "FAKE PROMPT"

        # Prepare a fake config with max_iterations set (so the or-3 path uses this value)
        class Cfg:
            pass

        cfg = Cfg()
        cfg.max_iterations = 5
        cfg.strategic_llm_model = "strategic-model"
        cfg.strategic_llm_provider = "strategic-provider"
        cfg.llm_kwargs = {}
        cfg.strategic_token_limit = 50
        cfg.smart_llm_model = "smart-model"
        cfg.temperature = 0.2
        cfg.smart_token_limit = 30
        cfg.smart_llm_provider = "smart-provider"

        # Fake async create_chat_completion that returns a JSON list string
        async def fake_create_chat_completion(*args, **kwargs):
            # basic sanity checks to ensure generate_sub_queries forwarded inputs
            # model should be the strategic model on first try
            assert kwargs.get("model") == cfg.strategic_llm_model
            messages = kwargs.get("messages")
            assert isinstance(messages, list) and messages[0]["role"] == "user"
            # return a JSON list string that json_repair.loads can parse
            return '["sub-query-1", "sub-query-2"]'

        # Patch the create_chat_completion name in the globals of the function under test
        original_create = generate_sub_queries.__globals__.get("create_chat_completion")
        generate_sub_queries.__globals__["create_chat_completion"] = fake_create_chat_completion

        try:
            # Run the async function via __import__('asyncio') to avoid needing an import statement
            asyncio_mod = __import__("asyncio")
            result = asyncio_mod.get_event_loop().run_until_complete(
                generate_sub_queries(
                    query="original query",
                    parent_query="parent query",
                    report_type="report-type",
                    context=[{"doc": "1"}],
                    cfg=cfg,
                    cost_callback=None,
                    prompt_family=FakePromptFamily(),
                )
            )
        finally:
            # Restore original create_chat_completion to avoid side effects
            generate_sub_queries.__globals__["create_chat_completion"] = original_create

        # Verify the prompt family was called with the expected max_iterations from cfg
        self.assertIn("args", called)
        self.assertEqual(called["args"]["query"], "original query")
        self.assertEqual(called["args"]["parent_query"], "parent query")
        self.assertEqual(called["args"]["report_type"], "report-type")
        self.assertEqual(called["args"]["max_iterations"], cfg.max_iterations)
        self.assertEqual(called["args"]["context"], [{"doc": "1"}])

        # Verify the returned value is the parsed list
        self.assertEqual(result, ["sub-query-1", "sub-query-2"])
