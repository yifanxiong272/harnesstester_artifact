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
        """Ensure system_instruction returned by the serializer is added to config passed to the API."""
        # Prepare inputs and sentinel values
        messages = []  # content doesn't matter; serializer will be patched
        RESP_TEXT = "hello from gemini"
        SYS_INSTR = "This is a system instruction"

        # Create a simple response object the fake generate_content will return
        class FakeResponse:
            pass

        fake_response = FakeResponse()
        fake_response.text = RESP_TEXT
        fake_response.usage_metadata = None
        fake_response.parsed = None
        fake_response.candidates = []

        # Capture the config passed into generate_content
        captured_config = {}

        async def fake_generate_content(model, contents, config):
            # store a shallow copy so assertions can inspect it later
            captured_config.update(dict(config))
            return fake_response

        # Build a fake client with the nested aio.models.generate_content coroutine
        class Dummy:
            pass

        fake_client = Dummy()
        fake_client.aio = Dummy()
        fake_client.aio.models = Dummy()
        fake_client.aio.models.generate_content = fake_generate_content

        # Patch the serializer to return a non-empty system instruction and the get_client method
        with unittest.mock.patch.object(
            GoogleMessageSerializer, 'serialize_messages', return_value=(["user content"], SYS_INSTR)
        ), unittest.mock.patch.object(
            ChatGoogle, 'get_client', return_value=fake_client
        ):
            # Instantiate the ChatGoogle model (minimal required args)
            llm = ChatGoogle(model='gemini-2.0')

            # Call ainvoke and run the coroutine
            result = asyncio.run(llm.ainvoke(messages))

        # Assertions: ensure we got the expected completion and the system_instruction made it into config
        self.assertIsInstance(result, ChatInvokeCompletion)
        self.assertEqual(result.completion, RESP_TEXT)
        self.assertIn('system_instruction', captured_config)
        self.assertEqual(captured_config['system_instruction'], SYS_INSTR)
        # Also ensure temperature was set by the function (model does not contain 'gemini-3')
        self.assertIn('temperature', captured_config)
        self.assertEqual(captured_config['temperature'], 0.5)
