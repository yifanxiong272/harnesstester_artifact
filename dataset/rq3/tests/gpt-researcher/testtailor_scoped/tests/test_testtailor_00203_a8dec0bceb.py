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
        """Ensure reasoning_effort is added to provider kwargs when model supports it."""
        # Prepare
        fn_globals = create_chat_completion.__globals__

        # Backup originals to restore later
        orig_get_llm = fn_globals.get('get_llm')
        orig_support = fn_globals.get('SUPPORT_REASONING_EFFORT_MODELS')

        captured_kwargs = []

        # Fake provider that returns a non-empty response
        class FakeProvider:
            last_response_metadata = {"meta": True}
            last_usage_metadata = {"usage": 1}

            async def get_chat_response(self, messages, stream, websocket, **kwargs):
                # just return a simple non-empty response
                return "fake-response"

        def fake_get_llm(llm_provider, **kwargs):
            # capture the kwargs passed when creating the provider
            captured_kwargs.append(kwargs)
            return FakeProvider()

        # Put a model name into the SUPPORT_REASONING_EFFORT_MODELS set
        test_model = "test-model-reason"
        fn_globals['SUPPORT_REASONING_EFFORT_MODELS'] = {test_model}
        fn_globals['get_llm'] = fake_get_llm

        # Use the ReasoningEfforts enum from the function's globals to pick a value
        ReasoningEfforts_enum = fn_globals['ReasoningEfforts']
        reasoning_value = ReasoningEfforts_enum.High.value

        try:
            # Call the async function synchronously
            response = asyncio.get_event_loop().run_until_complete(
                create_chat_completion(
                    messages=[{"role": "user", "content": "hello"}],
                    model=test_model,
                    llm_provider="any-provider",
                    reasoning_effort=reasoning_value,
                )
            )

            # Assertions
            self.assertEqual(response, "fake-response")
            # Ensure get_llm was called and reasoning_effort was included in kwargs
            self.assertTrue(captured_kwargs, "get_llm was not called")
            self.assertIn('reasoning_effort', captured_kwargs[0])
            self.assertEqual(captured_kwargs[0]['reasoning_effort'], reasoning_value)
        finally:
            # Restore originals
            if orig_get_llm is not None:
                fn_globals['get_llm'] = orig_get_llm
            else:
                fn_globals.pop('get_llm', None)
            if orig_support is not None:
                fn_globals['SUPPORT_REASONING_EFFORT_MODELS'] = orig_support
            else:
                fn_globals.pop('SUPPORT_REASONING_EFFORT_MODELS', None)
