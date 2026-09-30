import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.deep_research.example')
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
        """Test generate_serp_queries returns parsed queries when LLM returns JSON array."""
        # Prepare a fake LLM response (valid JSON array per schema)
        fake_response = (
            '[{"query": "benefits of intermittent fasting", "researchGoal": "Summarize proven health benefits"}, '
            '{"query": "intermittent fasting risks", "researchGoal": "Identify potential risks and contraindications"}, '
            '{"query": "intermittent fasting protocols comparison", "researchGoal": "Compare common fasting protocols"}]'
        )

        # Async stub to replace create_chat_completion used by DeepResearch.generate_serp_queries
        async def fake_create_chat_completion(messages, llm_provider=None, model=None, temperature=None, max_tokens=None, **kwargs):
            return fake_response

        # Patch the create_chat_completion in the function's globals so the method will use our stub
        globals_dict = DeepResearch.generate_serp_queries.__globals__
        original_create = globals_dict.get("create_chat_completion")
        globals_dict["create_chat_completion"] = fake_create_chat_completion

        try:
            # Instantiate DeepResearch and run generate_serp_queries
            dr = DeepResearch(query="intermittent fasting", breadth=3, depth=1)
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(dr.generate_serp_queries(query="intermittent fasting", num_queries=3))

            # Validate results
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
            for item in result:
                self.assertIsInstance(item, dict)
                self.assertIn("query", item)
                self.assertIn("researchGoal", item)
                self.assertTrue(item["query"])
                self.assertTrue(item["researchGoal"])

            # Check first item content matches the fake response (trimmed)
            self.assertEqual(result[0]["query"], "benefits of intermittent fasting")
            self.assertEqual(result[0]["researchGoal"], "Summarize proven health benefits")

        finally:
            # Restore original function to avoid side effects
            if original_create is not None:
                globals_dict["create_chat_completion"] = original_create
