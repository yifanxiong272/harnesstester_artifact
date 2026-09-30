import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.ollama.chat')
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
        """complete the test case here"""
        # Prepare a fake response object that matches the shape expected by the code under test
        class MessageContainer:
            def __init__(self, content):
                self.content = content

        class Response:
            def __init__(self, content):
                self.message = MessageContainer(content)

        response = Response('hello from ollama')

        # Dummy async chat callable to simulate the client's chat method
        class DummyChat:
            def __init__(self, resp):
                self.resp = resp
                self.called = 0
                self.last_args = None
                self.last_kwargs = None

            async def __call__(self, *args, **kwargs):
                self.called += 1
                self.last_args = args
                self.last_kwargs = kwargs
                return self.resp

        dummy_chat = DummyChat(response)
        # Create a simple mock client with a chat attribute
        class MockClient:
            pass

        mock_client = MockClient()
        mock_client.chat = dummy_chat

        # Instantiate the ChatOllama model and patch its get_client to return our mock client
        model = ChatOllama(model='test-model')
        # Override instance method to return our mock client
        model.get_client = lambda: mock_client

        # Use __import__ to obtain asyncio without adding an import statement at top level
        asyncio = __import__('asyncio')

        # Call the async ainvoke via asyncio.run
        result = asyncio.run(model.ainvoke(messages=[]))

        # Assertions: ensure we got the expected completion and usage is None
        self.assertIsInstance(result, ChatInvokeCompletion)
        self.assertEqual(result.completion, 'hello from ollama')
        self.assertIsNone(result.usage)

        # Ensure the mock client's chat was awaited exactly once and called with expected kwargs
        self.assertEqual(dummy_chat.called, 1)
        # The code calls chat with keyword args model, messages, options
        self.assertIn('model', dummy_chat.last_kwargs)
        self.assertEqual(dummy_chat.last_kwargs['model'], 'test-model')
        self.assertIn('messages', dummy_chat.last_kwargs)
        self.assertIn('options', dummy_chat.last_kwargs)
        # options should be the instance's ollama_options (default None)
        self.assertIs(dummy_chat.last_kwargs['options'], model.ollama_options)
