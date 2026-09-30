import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.chat')
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
        """Test that ainvoke with no output_format routes to _invoke_regular_completion and returns expected completion and usage."""
        import asyncio

        # Prepare inputs and expected serialized messages
        messages = ["ignored input objects"]
        groq_messages = [{"role": "user", "content": "hello"}]

        # Build a fake response that the mocked client will return using mocks (avoid extra imports)
        fake_message = unittest.mock.MagicMock()
        fake_message.content = "hello world"
        fake_choice = unittest.mock.MagicMock()
        fake_choice.message = fake_message
        fake_usage = unittest.mock.MagicMock()
        fake_usage.prompt_tokens = 1
        fake_usage.completion_tokens = 2
        fake_usage.total_tokens = 3
        fake_response = unittest.mock.MagicMock()
        fake_response.choices = [fake_choice]
        fake_response.usage = fake_usage

        # Mock client and its nested chat.completions.create async method
        mock_client = unittest.mock.MagicMock()
        mock_chat = unittest.mock.MagicMock()
        mock_completions = unittest.mock.MagicMock()
        mock_completions.create = unittest.mock.AsyncMock(return_value=fake_response)
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat

        # Instantiate ChatGroq
        chat = ChatGroq(model="g-test-model")

        # Patch the serializer and the get_client method to use our mocks
        with unittest.mock.patch.object(GroqMessageSerializer, "serialize_messages", return_value=groq_messages) as _ser_patch, \
             unittest.mock.patch.object(ChatGroq, "get_client", return_value=mock_client) as _gc_patch:

            # Call the async ainvoke via asyncio.run
            result = asyncio.run(chat.ainvoke(messages))

            # Assertions: ensure completion and usage returned as expected
            self.assertIsInstance(result, ChatInvokeCompletion)
            self.assertEqual(result.completion, "hello world")
            self.assertIsNotNone(result.usage)
            self.assertEqual(result.usage.prompt_tokens, 1)
            self.assertEqual(result.usage.completion_tokens, 2)
            self.assertEqual(result.usage.total_tokens, 3)

            # Ensure the client's create method was awaited with the serialized messages and model
            mock_completions.create.assert_awaited_once()
            called_kwargs = mock_completions.create.call_args.kwargs
            self.assertEqual(called_kwargs.get("messages"), groq_messages)
            self.assertEqual(called_kwargs.get("model"), chat.model)
            # defaults
            self.assertEqual(called_kwargs.get("service_tier"), chat.service_tier)
            self.assertEqual(called_kwargs.get("temperature"), chat.temperature)
            self.assertEqual(called_kwargs.get("top_p"), chat.top_p)
            self.assertEqual(called_kwargs.get("seed"), chat.seed)
