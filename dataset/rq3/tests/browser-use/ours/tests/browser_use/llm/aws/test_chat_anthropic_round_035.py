import asyncio
import json
import pytest

import browser_use.llm.aws.chat_anthropic as chat_mod
from browser_use.llm.views import ChatInvokeCompletion
from browser_use.llm.exceptions import ModelProviderError

# Helpers used across tests
class DummyTextBlock:
    def __init__(self, text):
        self.text = text

class DummyNonTextBlock:
    def __init__(self, value):
        self.value = value

class DummyContentBlock:
    def __init__(self, typ, inp):
        self.type = typ
        self.input = inp

class FakeMessagesClient:
    def __init__(self, create_impl):
        # create_impl is an async callable
        self._create_impl = create_impl

    @property
    def messages(self):
        # Provide an object with async create
        class _M:
            def __init__(self, impl):
                self._impl = impl

            async def create(self, *args, **kwargs):
                return await self._impl(*args, **kwargs)

        return _M(self._create_impl)


# Utility to build a bare instance of ChatAnthropicBedrock with overridden collaborators
def make_instance(monkeypatch, create_impl):
    # Patch the message serializer to a deterministic return
    monkeypatch.setattr(chat_mod, "AnthropicMessageSerializer", type("S", (), {"serialize_messages": staticmethod(lambda messages: ([{"role": "user", "content": "x"}], None))}))

    # Replace the read-only 'name' property on the class with a simple attribute for tests
    monkeypatch.setattr(chat_mod.ChatAnthropicBedrock, "name", "dummy-name", raising=False)

    inst = chat_mod.ChatAnthropicBedrock.__new__(chat_mod.ChatAnthropicBedrock)
    # Minimal attributes referenced in ainvoke
    inst.model = "dummy"
    # Provide a fake client where messages.create is the provided async impl
    client = FakeMessagesClient(create_impl)
    inst.get_client = lambda: client
    inst._get_client_params_for_invoke = lambda: {}
    inst._get_usage = lambda response: {"usage_marker": True}
    return inst

@pytest.mark.asyncio
async def test_textblock_response_round_035(monkeypatch):
    # Ensure isinstance uses the dummy TextBlock type
    monkeypatch.setattr(chat_mod, "TextBlock", DummyTextBlock)

    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                self.content = [DummyTextBlock("hello world")]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    res = await inst.ainvoke(messages=[object()], output_format=None)

    assert isinstance(res, ChatInvokeCompletion)
    assert res.completion == "hello world"
    assert res.usage == {"usage_marker": True}


@pytest.mark.asyncio
async def test_non_textblock_response_round_035(monkeypatch):
    # Non-TextBlock content should be converted with str()
    monkeypatch.setattr(chat_mod, "TextBlock", DummyTextBlock)

    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                self.content = [DummyNonTextBlock(12345)]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    res = await inst.ainvoke(messages=[object()], output_format=None)

    assert isinstance(res, ChatInvokeCompletion)
    # The code uses str() on the content block
    assert res.completion == str(DummyNonTextBlock(12345))
    assert res.usage == {"usage_marker": True}


@pytest.mark.asyncio
async def test_tool_successful_validation_round_035(monkeypatch):
    # Structured output path: returns a tool_use block that validates cleanly
    # Create an output_format type with required methods
    class OutputFormat:
        __name__ = "MyFormat"

        @staticmethod
        def model_json_schema():
            # include 'title' to exercise deletion branch
            return {"title": "T", "properties": {"a": {"type": "integer"}}}

        @staticmethod
        def model_validate(value):
            # Simulate pydantic-style validation returning a transformed object
            return {"validated": value}

    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                self.content = [DummyContentBlock("tool_use", {"a": 1})]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    res = await inst.ainvoke(messages=[object()], output_format=OutputFormat)

    assert isinstance(res, ChatInvokeCompletion)
    assert res.completion == {"validated": {"a": 1}}
    assert res.usage == {"usage_marker": True}


@pytest.mark.asyncio
async def test_tool_validation_json_handling_round_035(monkeypatch):
    # Test the exception handling path where model_validate fails first,
    # and input is a JSON string which gets json.loads'ed, then validated.
    class OutputFormat:
        __name__ = "Fmt2"
        _calls = 0

        @staticmethod
        def model_json_schema():
            return {"properties": {"x": {"type": "array"}}}

        @classmethod
        def model_validate(cls, value):
            # First call fails to trigger the except: subsequent calls succeed
            cls._calls += 1
            if cls._calls == 1:
                raise Exception("first-try-fail")
            return {"ok": value}

    # Input will be a JSON string, causing json.loads to produce a dict
    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                self.content = [DummyContentBlock("tool_use", json.dumps({"x": [1, 2]}))]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    res = await inst.ainvoke(messages=[object()], output_format=OutputFormat)

    assert isinstance(res, ChatInvokeCompletion)
    assert res.completion == {"ok": {"x": [1, 2]}}
    assert res.usage == {"usage_marker": True}


@pytest.mark.asyncio
async def test_tool_double_serialized_field_round_035(monkeypatch):
    # Test the branch where a dict input contains stringified JSON values (double-serialized)
    class OutputFormat:
        __name__ = "Fmt3"
        _calls = 0

        @staticmethod
        def model_json_schema():
            return {"properties": {"items": {"type": "array"}}}

        @classmethod
        def model_validate(cls, value):
            cls._calls += 1
            if cls._calls == 1:
                # force the code path into the except branch
                raise Exception("need-fix")
            return {"fixed": value}

    # Provide a dict where one field is a JSON list as string
    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                self.content = [DummyContentBlock("tool_use", {"items": "[1, 2, 3]", "other": "nochange"})]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    res = await inst.ainvoke(messages=[object()], output_format=OutputFormat)

    assert isinstance(res, ChatInvokeCompletion)
    # After cleaning, model_validate should be called and return the fixed structure
    assert res.completion == {"fixed": {"items": [1, 2, 3], "other": "nochange"}}


@pytest.mark.asyncio
async def test_no_tool_use_raises_round_035(monkeypatch):
    # When output_format is provided but no content block of type 'tool_use' exists
    class OutputFormat:
        __name__ = "NoTool"

        @staticmethod
        def model_json_schema():
            return {"properties": {}}

        @staticmethod
        def model_validate(value):
            return value

    async def create_impl(*args, **kwargs):
        class Resp:
            def __init__(self):
                # content lacks any 'tool_use' typed block
                self.content = [DummyContentBlock("text", "something")]
        return Resp()

    inst = make_instance(monkeypatch, create_impl)

    with pytest.raises(ValueError) as exc:
        await inst.ainvoke(messages=[object()], output_format=OutputFormat)

    assert "Expected tool use in response" in str(exc.value)


@pytest.mark.asyncio
async def test_api_connection_error_mapping_round_035(monkeypatch):
    # Simulate an APIConnectionError being raised by the client and ensure it is mapped
    # to ModelProviderError with message preserved.
    class FakeAPIConnectionError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    # Patch the APIConnectionError name the module uses
    monkeypatch.setattr(chat_mod, "APIConnectionError", FakeAPIConnectionError)

    async def create_impl(*args, **kwargs):
        raise FakeAPIConnectionError("conn-failed")

    inst = make_instance(monkeypatch, create_impl)

    with pytest.raises(ModelProviderError) as excinfo:
        await inst.ainvoke(messages=[object()], output_format=None)

    err = excinfo.value
    assert "conn-failed" in str(err)
