import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.utils.llms')
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
        """Ensure call_model constructs Config and converts messages before calling the LLM."""
        # Prepare trackers and fakes
        recorded = {}

        class DummyConfig:
            def __init__(self):
                # Values that call_model expects to read from Config instance
                self.smart_llm_provider = "dummy_provider"
                self.llm_kwargs = {"foo": "bar"}

        async def fake_create_chat_completion(
            model=None,
            messages=None,
            temperature=None,
            llm_provider=None,
            llm_kwargs=None,
            **kwargs,
        ):
            # Record what was passed in for assertions
            recorded["model"] = model
            recorded["messages"] = messages
            recorded["temperature"] = temperature
            recorded["llm_provider"] = llm_provider
            recorded["llm_kwargs"] = llm_kwargs
            recorded["extra_kwargs"] = kwargs
            return "fake-llm-response"

        def fake_convert_openai_messages(prompt):
            recorded["convert_called_with"] = prompt
            # Return a simple converted message structure expected by create_chat_completion
            return [{"role": "user", "content": "converted"}]

        # Patch globals used by call_model, preserving originals to restore later
        orig_create = call_model.__globals__.get("create_chat_completion")
        orig_Config = call_model.__globals__.get("Config")
        orig_convert = call_model.__globals__.get("convert_openai_messages")

        call_model.__globals__["create_chat_completion"] = fake_create_chat_completion
        call_model.__globals__["Config"] = DummyConfig
        call_model.__globals__["convert_openai_messages"] = fake_convert_openai_messages

        try:
            # Use __import__ to obtain asyncio without adding import statements at top
            asyncio = __import__("asyncio")
            # Execute the async function and get the result
            result = asyncio.run(
                call_model(prompt=[{"role": "user", "content": "hello"}], model="gpt-test-model")
            )

            # Assertions
            self.assertEqual(result, "fake-llm-response")
            # Ensure Config was used to supply llm_provider and llm_kwargs
            self.assertEqual(recorded["llm_provider"], "dummy_provider")
            self.assertEqual(recorded["llm_kwargs"], {"foo": "bar"})
            # Ensure the prompt was passed into convert_openai_messages
            self.assertIn("convert_called_with", recorded)
            self.assertEqual(recorded["convert_called_with"], [{"role": "user", "content": "hello"}])
            # Ensure the model name was forwarded
            self.assertEqual(recorded["model"], "gpt-test-model")
            # Ensure the converted messages were passed to create_chat_completion
            self.assertEqual(recorded["messages"], [{"role": "user", "content": "converted"}])

        finally:
            # Restore originals to avoid side effects on other tests
            if orig_create is not None:
                call_model.__globals__["create_chat_completion"] = orig_create
            else:
                del call_model.__globals__["create_chat_completion"]
            if orig_Config is not None:
                call_model.__globals__["Config"] = orig_Config
            else:
                del call_model.__globals__["Config"]
            if orig_convert is not None:
                call_model.__globals__["convert_openai_messages"] = orig_convert
            else:
                del call_model.__globals__["convert_openai_messages"]
