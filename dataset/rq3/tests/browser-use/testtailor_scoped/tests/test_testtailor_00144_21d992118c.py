import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.browser_use.chat')
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
        """Test that output_format.model_json_schema() is added to payload and response is validated."""
        # Dummy message object that mimics BaseMessage.model_dump()
        class DummyMessage:
            def model_dump(self):
                return {'role': 'user', 'content': 'hello'}

        # Define a pydantic model for output_format (expects pydantic v2 API)
        class MyFormat(BaseModel):
            foo: str

        client = ChatBrowserUse(api_key='test-api-key')

        # Replace _make_request with a fake that asserts the payload contains the schema
        async def fake_make_request(payload: dict) -> dict:
            # Ensure output_format was serialized into the payload
            assert 'output_format' in payload, "output_format key missing from payload"
            assert payload['output_format'] == MyFormat.model_json_schema()
            # Return a completion matching MyFormat schema
            return {'completion': {'foo': 'bar'}}

        client._make_request = fake_make_request  # type: ignore

        # Invoke and run the async method
        result = asyncio.run(client.ainvoke([DummyMessage()], output_format=MyFormat))

        # Assert the returned completion was validated into MyFormat
        self.assertIsInstance(result.completion, MyFormat)
        self.assertEqual(result.completion.foo, 'bar')
