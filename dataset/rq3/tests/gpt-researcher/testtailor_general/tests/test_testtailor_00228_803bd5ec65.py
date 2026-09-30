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
        """Test that llm_kwargs are merged into provider kwargs via update(llm_kwargs)."""
        messages = [{"role": "user", "content": "hello"}]
        model = "test-model"
        llm_kwargs = {"extra_option": "value123"}
        captured = {}

        class FakeProvider:
            def __init__(self):
                self.last_response_metadata = {"r": 1}
                self.last_usage_metadata = {"u": 2}

            async def get_chat_response(self, messages_arg, stream_arg, websocket_arg, **kwargs):
                # record what was passed and return a predictable response
                captured["messages_arg"] = messages_arg
                captured["stream_arg"] = stream_arg
                captured["websocket_arg"] = websocket_arg
                captured["get_chat_kwargs"] = kwargs
                return "fake-response"

        def fake_get_llm(llm_provider, **kwargs):
            # record the kwargs that were passed into get_llm
            captured["get_llm_called_with"] = {"llm_provider": llm_provider, **kwargs}
            return FakeProvider()

        # Monkeypatch the get_llm used by create_chat_completion
        orig_get_llm = create_chat_completion.__globals__.get("get_llm")
        create_chat_completion.__globals__["get_llm"] = fake_get_llm
        try:
            # call the async function synchronously for the test
            resp = asyncio.get_event_loop().run_until_complete(
                create_chat_completion(
                    messages=messages,
                    model=model,
                    llm_kwargs=llm_kwargs,
                    llm_provider="my-provider",
                )
            )

            # validate response and that llm_kwargs were merged into provider kwargs
            self.assertEqual(resp, "fake-response")
            called = captured.get("get_llm_called_with")
            self.assertIsNotNone(called, "get_llm was not called")
            # model should be present
            self.assertEqual(called.get("model"), model)
            # the custom llm_kwargs key should have been included via update(llm_kwargs)
            self.assertEqual(called.get("extra_option"), "value123")
        finally:
            # restore original get_llm
            if orig_get_llm is None:
                del create_chat_completion.__globals__["get_llm"]
            else:
                create_chat_completion.__globals__["get_llm"] = orig_get_llm
