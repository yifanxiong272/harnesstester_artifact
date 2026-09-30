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
        """When response_format='json', call_model should call parse_json_markdown with the LLM response and return its result."""
        # Preserve originals to restore later
        orig_create = call_model.__globals__.get("create_chat_completion")
        orig_parse_json = call_model.__globals__.get("parse_json_markdown")
        orig_Config = call_model.__globals__.get("Config")
        orig_convert = call_model.__globals__.get("convert_openai_messages")

        # Prepare replacements / fakes
        async def fake_create_chat_completion(*args, **kwargs):
            # record that it was called
            fake_create_chat_completion.called = True
            fake_create_chat_completion.last_args = args
            fake_create_chat_completion.last_kwargs = kwargs
            return "FAKE_MODEL_RESPONSE"

        def fake_parse_json_markdown(response, parser=None):
            # assert we get the model response
            assert response == "FAKE_MODEL_RESPONSE"
            # return a sentinel parsed object
            return {"parsed": True}

        class DummyConfig:
            def __init__(self):
                # call_model only reads these two attributes
                self.smart_llm_provider = "test_provider"
                self.llm_kwargs = {}

        def fake_convert_openai_messages(prompt):
            # just return something plausible for the LLM client
            return [{"role": "user", "content": "converted"}]

        # Patch into call_model's globals
        call_model.__globals__["create_chat_completion"] = fake_create_chat_completion
        call_model.__globals__["parse_json_markdown"] = fake_parse_json_markdown
        call_model.__globals__["Config"] = DummyConfig
        call_model.__globals__["convert_openai_messages"] = fake_convert_openai_messages

        try:
            # Use __import__ to get asyncio without an explicit import statement
            asyncio = __import__("asyncio")
            result = asyncio.run(
                call_model(prompt=[{"role": "user", "content": "hello"}], model="openai:test-model", response_format="json")
            )

            # Validate results and that our fake was used
            assert result == {"parsed": True}
            assert getattr(fake_create_chat_completion, "called", False) is True

            # also check that the fake_create received the converted messages
            called_args = getattr(fake_create_chat_completion, "last_args", ())
            called_kwargs = getattr(fake_create_chat_completion, "last_kwargs", {})
            # ensure the provider/model was passed through
            assert called_kwargs.get("model") == "openai:test-model"
            # ensure messages were passed (converted)
            if called_args:
                passed_messages = called_args[0]
            else:
                passed_messages = called_kwargs.get("messages")
            assert passed_messages == [{"role": "user", "content": "converted"}]

        finally:
            # Restore originals
            if orig_create is not None:
                call_model.__globals__["create_chat_completion"] = orig_create
            else:
                call_model.__globals__.pop("create_chat_completion", None)

            if orig_parse_json is not None:
                call_model.__globals__["parse_json_markdown"] = orig_parse_json
            else:
                call_model.__globals__.pop("parse_json_markdown", None)

            if orig_Config is not None:
                call_model.__globals__["Config"] = orig_Config
            else:
                call_model.__globals__.pop("Config", None)

            if orig_convert is not None:
                call_model.__globals__["convert_openai_messages"] = orig_convert
            else:
                call_model.__globals__.pop("convert_openai_messages", None)
