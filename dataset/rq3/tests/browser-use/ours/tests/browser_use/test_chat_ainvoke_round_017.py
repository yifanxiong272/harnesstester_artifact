import asyncio
from types import SimpleNamespace
import pytest

import browser_use.llm.openai.chat as chat_mod

# Helpers for creating fake responses
class FakeChoice:
    def __init__(self, content, finish_reason="stop"):
        self.message = SimpleNamespace(content=content)
        self.finish_reason = finish_reason

class FakeResponse:
    def __init__(self, choices):
        self.choices = choices

class DummyOutputModel:
    @classmethod
    def model_validate_json(cls, json_text):
        # deterministic: return a dict indicating it was parsed
        return {"parsed": True, "src": json_text}

# Simple fake ChatCompletionContentPartTextParam replacement
class FakeContentPart:
    def __init__(self, text, type):
        self.text = text
        self.type = type

# Simple ResponseFormatJSONSchema placeholder
class FakeResponseFormat:
    def __init__(self, json_schema, type):
        self.json_schema = json_schema
        self.type = type

@pytest.mark.asyncio
async def test_reasoning_models_and_string_response_round_017(monkeypatch):
    """
    Ensure reasoning_models matching model causes reasoning_effort to be passed and
    temperature/frequency_penalty to be removed from model params, and a normal
    string response returns the expected completion and stop_reason.
    """
    # Prepare openai_messages returned by serializer
    openai_messages = [{"role": "user", "content": "hello"}]
    monkeypatch.setattr(chat_mod, "OpenAIMessageSerializer", SimpleNamespace(serialize_messages=lambda msgs: openai_messages))

    # Replace SchemaOptimizer just in case invoked elsewhere
    monkeypatch.setattr(chat_mod, "SchemaOptimizer", SimpleNamespace(create_optimized_json_schema=lambda *args, **kwargs: {"schema": "ok"}))

    captured = {}

    class FakeCompletions:
        async def create(self_self, **kwargs):
            # capture kwargs to assert model params
            captured.update(kwargs)
            return FakeResponse([FakeChoice(content="reply-text", finish_reason="finished")])

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    # Build a minimal self object to bind to ainvoke
    self_obj = SimpleNamespace()
    # Set attributes that ainvoke reads
    self_obj.temperature = 0.9
    self_obj.frequency_penalty = 0.4
    self_obj.max_completion_tokens = None
    self_obj.top_p = None
    self_obj.seed = None
    self_obj.service_tier = None
    self_obj.reasoning_models = ["gpt"]
    self_obj.reasoning_effort = "high"
    self_obj.model = "gpt-4"
    self_obj.base_url = None
    self_obj.add_schema_to_system_prompt = False
    self_obj.remove_min_items_from_schema = False
    self_obj.remove_defaults_from_schema = False
    self_obj.dont_force_structured_output = True
    self_obj.name = "test-model"
    self_obj._get_usage = lambda response: {"tokens": 1}
    self_obj.get_client = lambda: FakeClient()

    # Bind and call the async ainvoke
    coro = chat_mod.ChatOpenAI.ainvoke.__get__(self_obj, chat_mod.ChatOpenAI)
    result = await coro(messages=["ignored"], output_format=None)

    assert result.completion == "reply-text"
    assert result.stop_reason == "finished"
    # Ensure reasoning_effort was passed
    assert "reasoning_effort" in captured and captured["reasoning_effort"] == "high"
    # Ensure popped fields are not present
    assert "temperature" not in captured
    assert "frequency_penalty" not in captured


@pytest.mark.asyncio
async def test_missing_choices_raises_modelprovider_round_017(monkeypatch):
    """
    When the provider returns no choices, ainvoke should raise ModelProviderError with status_code 502
    and include base_url hint when base_url is set.
    """
    openai_messages = [{"role": "system", "content": "sys"}]
    monkeypatch.setattr(chat_mod, "OpenAIMessageSerializer", SimpleNamespace(serialize_messages=lambda msgs: openai_messages))

    class FakeCompletionsEmpty:
        async def create(self_self, **kwargs):
            return FakeResponse([])

    class FakeChatEmpty:
        def __init__(self):
            self.completions = FakeCompletionsEmpty()

    class FakeClientEmpty:
        def __init__(self):
            self.chat = FakeChatEmpty()

    self_obj = SimpleNamespace()
    self_obj.temperature = None
    self_obj.frequency_penalty = None
    self_obj.max_completion_tokens = None
    self_obj.top_p = None
    self_obj.seed = None
    self_obj.service_tier = None
    self_obj.reasoning_models = []
    self_obj.reasoning_effort = None
    self_obj.model = "any"
    self_obj.base_url = "http://proxy"
    self_obj.add_schema_to_system_prompt = False
    self_obj.remove_min_items_from_schema = False
    self_obj.remove_defaults_from_schema = False
    self_obj.dont_force_structured_output = True
    self_obj.name = "proxy-model"
    self_obj._get_usage = lambda response: {}
    self_obj.get_client = lambda: FakeClientEmpty()

    coro = chat_mod.ChatOpenAI.ainvoke.__get__(self_obj, chat_mod.ChatOpenAI)
    with pytest.raises(chat_mod.ModelProviderError) as exc:
        await coro(messages=["ignored"], output_format=None)

    err = exc.value
    # Should map to 502 per code path
    assert getattr(err, "status_code", None) == 502
    # Message should include base_url hint
    assert "base_url=http://proxy" in str(getattr(err, "message", err))
    assert getattr(err, "model", None) == "proxy-model"


@pytest.mark.asyncio
async def test_structured_output_content_none_raises_round_017(monkeypatch):
    """
    If structured mode is used and the choice.message.content is None, expect ModelProviderError with 500.
    """
    openai_messages = [{"role": "system", "content": "sys"}]
    monkeypatch.setattr(chat_mod, "OpenAIMessageSerializer", SimpleNamespace(serialize_messages=lambda msgs: openai_messages))

    class FakeCompletionsNoneContent:
        async def create(self_self, **kwargs):
            return FakeResponse([FakeChoice(content=None)])

    class FakeChatNoneContent:
        def __init__(self):
            self.completions = FakeCompletionsNoneContent()

    class FakeClientNoneContent:
        def __init__(self):
            self.chat = FakeChatNoneContent()

    self_obj = SimpleNamespace()
    self_obj.temperature = None
    self_obj.frequency_penalty = None
    self_obj.max_completion_tokens = None
    self_obj.top_p = None
    self_obj.seed = None
    self_obj.service_tier = None
    self_obj.reasoning_models = []
    self_obj.reasoning_effort = None
    self_obj.model = "any"
    self_obj.base_url = None
    self_obj.add_schema_to_system_prompt = False
    self_obj.remove_min_items_from_schema = False
    self_obj.remove_defaults_from_schema = False
    self_obj.dont_force_structured_output = False
    self_obj.name = "struct-model"
    self_obj._get_usage = lambda response: {}
    self_obj.get_client = lambda: FakeClientNoneContent()

    coro = chat_mod.ChatOpenAI.ainvoke.__get__(self_obj, chat_mod.ChatOpenAI)
    with pytest.raises(chat_mod.ModelProviderError) as exc:
        await coro(messages=["ignored"], output_format=DummyOutputModel)

    err = exc.value
    assert getattr(err, "status_code", None) == 500
    assert "Failed to parse structured output from model response" in str(getattr(err, "message", err))
    assert getattr(err, "model", None) == "struct-model"


@pytest.mark.asyncio
async def test_add_schema_to_system_prompt_iterable_and_response_format_round_017(monkeypatch):
    """
    Cover the branch where add_schema_to_system_prompt is True and the first message content is iterable;
    ensure ChatCompletionContentPartTextParam is appended and response uses ResponseFormatJSONSchema.
    """
    # Make the initial message content be an iterable (list)
    orig_content = ["part1"]
    openai_messages = [{"role": "system", "content": orig_content}]
    monkeypatch.setattr(chat_mod, "OpenAIMessageSerializer", SimpleNamespace(serialize_messages=lambda msgs: openai_messages))

    # Patch ChatCompletionContentPartTextParam and ResponseFormatJSONSchema used by ainvoke
    monkeypatch.setattr(chat_mod, "ChatCompletionContentPartTextParam", FakeContentPart)
    monkeypatch.setattr(chat_mod, "ResponseFormatJSONSchema", FakeResponseFormat)
    monkeypatch.setattr(chat_mod, "SchemaOptimizer", SimpleNamespace(create_optimized_json_schema=lambda *args, **kwargs: {"opt": True}))

    captured = {}

    class FakeCompletionsCapture:
        async def create(self_self, **kwargs):
            captured["kwargs"] = kwargs
            # Return a structured response with a JSON string content
            return FakeResponse([FakeChoice(content='{"ok": true}', finish_reason="done")])

    class FakeChatCapture:
        def __init__(self):
            self.completions = FakeCompletionsCapture()

    class FakeClientCapture:
        def __init__(self):
            self.chat = FakeChatCapture()

    self_obj = SimpleNamespace()
    self_obj.temperature = None
    self_obj.frequency_penalty = None
    self_obj.max_completion_tokens = None
    self_obj.top_p = None
    self_obj.seed = None
    self_obj.service_tier = None
    self_obj.reasoning_models = []
    self_obj.reasoning_effort = None
    self_obj.model = "any"
    self_obj.base_url = None
    self_obj.add_schema_to_system_prompt = True
    self_obj.remove_min_items_from_schema = False
    self_obj.remove_defaults_from_schema = False
    self_obj.dont_force_structured_output = False
    self_obj.name = "schema-model"
    self_obj._get_usage = lambda response: {"u": 1}
    self_obj.get_client = lambda: FakeClientCapture()

    coro = chat_mod.ChatOpenAI.ainvoke.__get__(self_obj, chat_mod.ChatOpenAI)
    result = await coro(messages=["ignored"], output_format=DummyOutputModel)

    # Ensure response was parsed and returned
    assert result.completion == {"parsed": True, "src": '{"ok": true}'}
    # Ensure create was called with a response_format (structured path)
    assert "response_format" in captured["kwargs"]

    # Ensure the first message content was converted to a list with our FakeContentPart appended
    sent_messages = captured["kwargs"]["messages"]
    new_content = sent_messages[0]["content"]
    assert isinstance(new_content, list)
    last_part = new_content[-1]
    assert isinstance(last_part, FakeContentPart)
    assert "<json_schema>" in last_part.text


@pytest.mark.asyncio
async def test_error_mappings_rate_api_conn_status_round_017(monkeypatch):
    """
    Ensure exceptions from the client are mapped to the library-specific errors:
    - RateLimitError -> ModelRateLimitError
    - APIConnectionError -> ModelProviderError
    - APIStatusError -> ModelProviderError preserving status_code
    """
    openai_messages = [{"role": "user", "content": "x"}]
    monkeypatch.setattr(chat_mod, "OpenAIMessageSerializer", SimpleNamespace(serialize_messages=lambda msgs: openai_messages))

    # Create three fake exception classes with the attributes expected by ainvoke
    class FakeRateLimit(Exception):
        def __init__(self, message="limit"):
            self.message = message

    class FakeAPIConn(Exception):
        def __init__(self, msg="conn"):
            super().__init__(msg)
            self.args = (msg,)

    class FakeAPIStatus(Exception):
        def __init__(self, message="status", status_code=418):
            self.message = message
            self.status_code = status_code

    # Patch the module exception names
    monkeypatch.setattr(chat_mod, "RateLimitError", FakeRateLimit)
    monkeypatch.setattr(chat_mod, "APIConnectionError", FakeAPIConn)
    monkeypatch.setattr(chat_mod, "APIStatusError", FakeAPIStatus)

    # Helper to run a scenario where create raises exc
    async def run_with_exc(exc_cls, exc_instance):
        class FakeCompletionsRaise:
            async def create(self_self, **kwargs):
                raise exc_instance

        class FakeChatRaise:
            def __init__(self):
                self.completions = FakeCompletionsRaise()

        class FakeClientRaise:
            def __init__(self):
                self.chat = FakeChatRaise()

        self_obj = SimpleNamespace()
        self_obj.temperature = None
        self_obj.frequency_penalty = None
        self_obj.max_completion_tokens = None
        self_obj.top_p = None
        self_obj.seed = None
        self_obj.service_tier = None
        self_obj.reasoning_models = []
        self_obj.reasoning_effort = None
        self_obj.model = "any"
        self_obj.base_url = None
        self_obj.add_schema_to_system_prompt = False
        self_obj.remove_min_items_from_schema = False
        self_obj.remove_defaults_from_schema = False
        self_obj.dont_force_structured_output = True
        self_obj.name = "err-model"
        self_obj._get_usage = lambda response: {}
        self_obj.get_client = lambda: FakeClientRaise()

        coro = chat_mod.ChatOpenAI.ainvoke.__get__(self_obj, chat_mod.ChatOpenAI)
        return coro(messages=["ignored"], output_format=None)

    # RateLimit -> ModelRateLimitError
    with pytest.raises(chat_mod.ModelRateLimitError) as excinfo_rate:
        await run_with_exc(FakeRateLimit, FakeRateLimit("too many"))
    assert getattr(excinfo_rate.value, "model", None) == "err-model"

    # APIConnectionError -> ModelProviderError
    with pytest.raises(chat_mod.ModelProviderError):
        await run_with_exc(FakeAPIConn, FakeAPIConn("conn lost"))

    # APIStatusError -> ModelProviderError and status preserved
    with pytest.raises(chat_mod.ModelProviderError) as excinfo_status:
        await run_with_exc(FakeAPIStatus, FakeAPIStatus(message="bad", status_code=499))
    assert getattr(excinfo_status.value, "status_code", None) == 499
