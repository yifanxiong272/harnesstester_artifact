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
        """Ensure generate_feedback builds the correct messages and calls create_chat_completion with expected args,
        and that the JSON response is parsed into a list of questions."""
        dr = DeepResearch(query="Explain quantum-safe cryptography")

        async def fake_create_chat_completion(*args, **kwargs):
            # Validate provider/model/params from kwargs
            self.assertEqual(kwargs.get("llm_provider"), LLM_PROVIDER)
            self.assertEqual(kwargs.get("model"), O3_MINI_MODEL)
            self.assertAlmostEqual(kwargs.get("temperature"), 0.7)
            self.assertEqual(kwargs.get("max_tokens"), 500)
            self.assertEqual(kwargs.get("reasoning_effort"), ReasoningEfforts.High.value)

            # The first positional arg (if present) or kwargs['messages'] contains the messages
            messages = None
            if args:
                messages = args[0]
            else:
                messages = kwargs.get("messages")

            # Validate message structure and content
            self.assertIsInstance(messages, list)
            self.assertGreaterEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("expert researcher", messages[0]["content"])
            self.assertIn("Return valid JSON only", messages[0]["content"])

            self.assertEqual(messages[1]["role"], "user")
            self.assertIn("ask some follow up questions", messages[1]["content"])
            # default num_questions is 3 in the call site
            self.assertIn("Return a maximum of 3 questions", messages[1]["content"])
            self.assertIn("Query: Explain quantum-safe cryptography", messages[1]["content"])

            # Return a valid JSON string consistent with expected schema
            return '{"questions": ["What is the desired deployment timeline?", "Which threat models are most important?"]}'

        # Patch the create_chat_completion used in the DeepResearch module
        module_path = DeepResearch.__module__ + ".create_chat_completion"
        with unittest.mock.patch(module_path, new=fake_create_chat_completion):
            loop = asyncio.get_event_loop()
            questions = loop.run_until_complete(dr.generate_feedback("Explain quantum-safe cryptography"))

        # Verify parsed output
        self.assertIsInstance(questions, list)
        self.assertEqual(len(questions), 2)
        self.assertIn("What is the desired deployment timeline?", questions)
        self.assertIn("Which threat models are most important?", questions)
