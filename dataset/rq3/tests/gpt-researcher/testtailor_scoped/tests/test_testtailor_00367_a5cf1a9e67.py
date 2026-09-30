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
        """Ensure OPENAI_BASE_URL is forwarded to the provider as openai_api_base."""
        base_url = "https://example.openai.local"
        os.environ["OPENAI_BASE_URL"] = base_url
        messages = [{"role": "user", "content": "Hello"}]

        async def runner():
            # Create a fake provider that returns a canned response
            class FakeProvider:
                last_response_metadata = {"meta": True}
                last_usage_metadata = {"usage": 1}

                async def get_chat_response(self, messages, stream, websocket, **kwargs):
                    return "fake-response"

            # Define a fake get_llm that asserts the openai_api_base was provided
            def fake_get_llm(llm_provider, **kwargs):
                assert llm_provider == "openai"
                assert kwargs.get("openai_api_base") == base_url
                assert kwargs.get("model") == "test-model"
                return FakeProvider()

            # Patch the get_llm used by create_chat_completion by injecting into its globals
            original_get_llm = create_chat_completion.__globals__.get("get_llm", None)
            create_chat_completion.__globals__["get_llm"] = fake_get_llm
            try:
                resp = await create_chat_completion(
                    messages=messages,
                    model="test-model",
                    llm_provider="openai",
                )
                return resp
            finally:
                # Restore original get_llm (or remove if it didn't exist)
                if original_get_llm is None:
                    create_chat_completion.__globals__.pop("get_llm", None)
                else:
                    create_chat_completion.__globals__["get_llm"] = original_get_llm

        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    new_loop = asyncio.new_event_loop()
                    try:
                        result = new_loop.run_until_complete(runner())
                    finally:
                        new_loop.close()
                else:
                    result = loop.run_until_complete(runner())
            except RuntimeError:
                result = asyncio.run(runner())
            self.assertEqual(result, "fake-response")
        finally:
            os.environ.pop("OPENAI_BASE_URL", None)
