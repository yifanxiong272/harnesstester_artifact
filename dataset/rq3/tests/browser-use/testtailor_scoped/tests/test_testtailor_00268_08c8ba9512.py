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
        """Ensure explicit temperature is placed into the config passed to the client."""
        # Create ChatGoogle with an explicit temperature to force the branch
        chat = ChatGoogle(model='gemini-2.0', temperature=0.42)

        # Create a fake client that captures the config passed to generate_content
        class FakeModels:
            def __init__(self):
                self.last_call = None

            async def generate_content(self, model, contents, config):
                # Capture call args for assertions
                self.last_call = {'model': model, 'contents': contents, 'config': config}
                class Resp:
                    pass
                r = Resp()
                r.text = "ok"
                r.usage_metadata = None
                r.candidates = []
                r.parsed = None
                return r

        class FakeAio:
            def __init__(self):
                self.models = FakeModels()

        fake_client = type("C", (), {})()
        fake_client.aio = FakeAio()

        # Inject the fake client into the ChatGoogle instance
        chat._client = fake_client

        # Call the async method synchronously
        import asyncio
        result = asyncio.run(chat.ainvoke(messages=[]))

        # Assert the completion is returned and the temperature was included in config
        self.assertEqual(result.completion, "ok")
        self.assertIsNotNone(chat._client.aio.models.last_call)
        called_config = chat._client.aio.models.last_call['config']
        # The target line sets config['temperature'] = self.temperature
        self.assertIn('temperature', called_config)
        self.assertEqual(called_config['temperature'], 0.42)
