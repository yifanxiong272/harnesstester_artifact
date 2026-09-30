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
        """Test generate_feedback returns parsed questions using a mocked LLM provider"""
        async def run_test():
            # Prepare a fake provider whose get_chat_response returns the expected JSON
            mock_provider = MagicMock()
            mock_provider.get_chat_response = AsyncMock(
                return_value='{"questions": ["What is your timeframe?", "Who is the target audience?"]}'
            )
            mock_provider.last_response_metadata = {}
            mock_provider.last_usage_metadata = {}

            # Patch get_llm so create_chat_completion uses our fake provider and does not hit OpenAI
            with patch("gpt_researcher.utils.llm.get_llm", return_value=mock_provider) as mock_get_llm:
                dr = DeepResearch(query="Investigate the effects of X on Y")
                questions = await dr.generate_feedback("Investigate the effects of X on Y", num_questions=2)

                # Verify output
                self.assertEqual(
                    questions,
                    ["What is your timeframe?", "Who is the target audience?"]
                )

                # Ensure get_llm was invoked to obtain our mock provider
                self.assertTrue(mock_get_llm.called)

        asyncio.run(run_test())
