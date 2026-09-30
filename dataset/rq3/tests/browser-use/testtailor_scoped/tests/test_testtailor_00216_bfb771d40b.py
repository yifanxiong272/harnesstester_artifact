import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.google.chat')
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
        """Ensure that when self.config is provided, ainvoke copies it and proceeds to call the client."""
        # Create a ChatGoogle instance with a non-empty config so code hits `config = self.config.copy()`
        chat = ChatGoogle(model='gemini-test', config={'foo': 'bar'})

        # Backup the real serializer and replace it with a stub to avoid needing real message objects
        original_serializer = GoogleMessageSerializer.serialize_messages
        GoogleMessageSerializer.serialize_messages = lambda messages, include_system_in_user=False: (['stub_content'], None)

        # Create a dummy client whose async generate_content returns a lightweight response object
        class DummyClient:
            class aio:
                class models:
                    @staticmethod
                    async def generate_content(model, contents, config):
                        resp = type('R', (), {})()
                        resp.text = 'hello world'
                        resp.candidates = [type('C', (), {'finish_reason': 'end_turn'})()]
                        resp.usage_metadata = None
                        resp.parsed = None
                        return resp

        # Patch the instance's get_client to return our dummy client
        chat.get_client = lambda: DummyClient()

        try:
            # Run the async ainvoke to exercise the code path
            result = asyncio.run(chat.ainvoke(messages=[object()], output_format=None))

            # Validate we got the expected ChatInvokeCompletion-like response
            self.assertEqual(result.completion, 'hello world')
            self.assertEqual(result.stop_reason, 'end_turn')

            # Ensure the original config on the instance was not mutated by the method (copy was used)
            self.assertEqual(chat.config, {'foo': 'bar'})
        finally:
            # Restore the original serializer to avoid side effects on other tests
            GoogleMessageSerializer.serialize_messages = original_serializer
