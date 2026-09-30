import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.chat')
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
        """Ensure temperature gets forwarded into the DeepSeek client create call."""
        # Arrange
        # Patch serializer to return a predictable DeepSeek message list
        orig_serializer = DeepSeekMessageSerializer.serialize_messages
        ds_messages = [{'role': 'user', 'content': 'hello'}]
        DeepSeekMessageSerializer.serialize_messages = lambda messages: ds_messages

        # Create a ChatDeepSeek instance with a specific temperature
        model = ChatDeepSeek(temperature=0.42)

        # Prepare a fake async response object: resp.choices[0].message.content == "hi"
        fake_resp = type('R', (), {})()
        fake_msg = type('M', (), {})()
        fake_msg.content = "hi"
        fake_choice = type('C', (), {})()
        fake_choice.message = fake_msg
        fake_resp.choices = [fake_choice]

        # Obtain AsyncMock without adding top-level imports
        AsyncMock = getattr(__import__('unittest.mock', fromlist=['AsyncMock']), 'AsyncMock')

        # AsyncMock for the create method to capture the kwargs it was called with
        create_mock = AsyncMock(return_value=fake_resp)

        # Build a fake client with the expected attribute structure
        fake_client = type('FC', (), {})()
        fake_client.chat = type('CH', (), {})()
        fake_client.chat.completions = type('COMP', (), {})()
        fake_client.chat.completions.create = create_mock

        # Replace the instance _client method to return our fake client
        model._client = lambda: fake_client

        try:
            # Act
            asyncio = __import__('asyncio')
            result = asyncio.run(model.ainvoke(messages=[]))

            # Assert result correctness
            self.assertIsInstance(result, ChatInvokeCompletion)
            self.assertEqual(result.completion, "hi")

            # Assert that the create method was awaited exactly once
            create_mock.assert_awaited_once()

            # Inspect the call kwargs to ensure temperature was forwarded
            called_kwargs = create_mock.call_args[1]  # kwargs dict
            self.assertEqual(called_kwargs.get('model'), model.model)
            self.assertIs(called_kwargs.get('messages'), ds_messages)
            self.assertEqual(called_kwargs.get('temperature'), 0.42)
        finally:
            # Restore serializer to avoid side effects on other tests
            DeepSeekMessageSerializer.serialize_messages = orig_serializer
