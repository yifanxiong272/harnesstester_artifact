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
        """Test that DeepResearch.process_serp_result calls the LLM and parses JSON learnings and follow-ups."""
        # Arrange
        dr = DeepResearch(query="irrelevant")

        # Prepare a fake LLM JSON response
        fake_response = (
            '{"learnings": ['
            '{"insight": "AI improves code quality", "sourceUrl": "https://example.com/article"},'
            '{"insight": "Tooling adoption is rising", "sourceUrl": ""}'
            '], '
            '"followUpQuestions": ["How to measure improvement?", "What datasets were used?"]}'
        )

        # Create a fake provider that returns the fake_response
        fake_provider = MagicMock()
        fake_provider.get_chat_response = AsyncMock(return_value=fake_response)
        fake_provider.last_response_metadata = {}
        fake_provider.last_usage_metadata = {}

        # Patch get_llm so create_chat_completion uses our fake provider and doesn't initialize real LLMs
        with patch("gpt_researcher.utils.llm.get_llm", return_value=fake_provider):
            # Act
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    dr.process_serp_result(query="test query", context="some search results", num_learnings=1)
                )
            finally:
                loop.close()

            # Assert
            self.assertIsInstance(result, dict)
            self.assertIn("learnings", result)
            self.assertIn("followUpQuestions", result)
            self.assertIn("citations", result)

            # Only top num_learnings (1) returned
            self.assertEqual(len(result["learnings"]), 1)
            self.assertEqual(result["learnings"][0], "AI improves code quality")

            # followUpQuestions truncated to num_learnings (1)
            self.assertEqual(len(result["followUpQuestions"]), 1)
            self.assertEqual(result["followUpQuestions"][0], "How to measure improvement?")

            # citations should map the returned learning to its URL
            self.assertIn("AI improves code quality", result["citations"])
            self.assertEqual(result["citations"]["AI improves code quality"], "https://example.com/article")
