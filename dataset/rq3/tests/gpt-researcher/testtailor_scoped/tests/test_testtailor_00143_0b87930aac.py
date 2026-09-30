import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.llm')
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
        """Ensure llm_kwargs are forwarded into provider kwargs via get_llm"""
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        llm_kwargs = {"custom_param": "custom_value"}
        recorded = {}

        class MockProvider:
            def __init__(self):
                self.last_response_metadata = {"meta": "value"}
                self.last_usage_metadata = {"usage": 1}

            async def get_chat_response(self, messages_arg, stream_arg, websocket_arg, **kwargs):
                # verify we receive the messages as passed (basic sanity)
                assert messages_arg == messages
                return "mocked-response"

        def fake_get_llm(llm_provider, **kwargs):
            # record what was passed to get_llm for later assertions
            recorded["llm_provider"] = llm_provider
            recorded["kwargs"] = kwargs.copy()
            return MockProvider()

        with unittest.mock.patch(f"{create_chat_completion.__module__}.get_llm", side_effect=fake_get_llm):
            # run the async function and get the response
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                create_chat_completion(
                    messages=messages,
                    model=model,
                    llm_kwargs=llm_kwargs,
                    llm_provider="test-provider",
                )
            )

        # Assertions: response returned and llm_kwargs were merged into provider kwargs
        self.assertEqual(response, "mocked-response")
        self.assertIn("custom_param", recorded["kwargs"])
        self.assertEqual(recorded["kwargs"]["custom_param"], "custom_value")
        self.assertIn("model", recorded["kwargs"])
        self.assertEqual(recorded["kwargs"]["model"], model)
        self.assertEqual(recorded["llm_provider"], "test-provider")
