import asyncio
from types import SimpleNamespace

import multi_agents.agents.utils.llms as llms


def test_call_model_returns_response_round_113(monkeypatch):
    # Arrange: fake Config, message conversion, and async chat completion
    class FakeConfig:
        def __init__(self):
            self.smart_llm_provider = "fake_provider"
            self.llm_kwargs = {"k": "v"}

    called = {}

    def fake_convert_openai_messages(prompt):
        called['convert_prompt'] = prompt
        return [{"role": "user", "content": "hello"}]

    async def fake_create_chat_completion(*args, **kwargs):
        # record how it was called and return a raw response
        called['create_args'] = args
        called['create_kwargs'] = kwargs
        return "RAW RESPONSE"

    # Patch symbols in the module under test
    monkeypatch.setattr(llms, "Config", FakeConfig)
    monkeypatch.setattr(llms, "convert_openai_messages", fake_convert_openai_messages)
    monkeypatch.setattr(llms, "create_chat_completion", fake_create_chat_completion)

    # Ensure parse_json_markdown would raise if called unexpectedly
    def fail_if_called(*args, **kwargs):
        raise AssertionError("parse_json_markdown should not be called in this test")

    monkeypatch.setattr(llms, "parse_json_markdown", fail_if_called)

    # Act
    prompt = [{"role": "user", "content": "hi"}]
    result = asyncio.run(llms.call_model(prompt=prompt, model="gpt-test", response_format=None))

    # Assert: returns raw response and passed expected kwargs to create_chat_completion
    assert result == "RAW RESPONSE"
    assert called['convert_prompt'] is prompt
    ck = called['create_kwargs']
    assert ck["model"] == "gpt-test"
    assert ck["messages"] == [{"role": "user", "content": "hello"}]
    assert ck["temperature"] == 0
    # Config was used to supply provider and llm_kwargs
    assert ck["llm_provider"] == "fake_provider"
    assert ck["llm_kwargs"] == {"k": "v"}


def test_call_model_parses_json_round_113(monkeypatch):
    # Arrange: similar setup but ensure json path is exercised
    class FakeConfig:
        def __init__(self):
            self.smart_llm_provider = "prov"
            self.llm_kwargs = {}

    def fake_convert_openai_messages(prompt):
        return [{"role": "user", "content": "ask"}]

    async def fake_create_chat_completion(*args, **kwargs):
        return "SOME MD WITH JSON"

    # Provide a fake json_repair.loads and a parse_json_markdown that ensures the parser passed through
    def fake_loads(s):
        # just a recognizer to assert identity
        return {"repaired": s}

    def fake_parse_json_markdown(response, parser=None):
        # verify parser is the json_repair.loads we provided and return a structured result
        assert parser is fake_loads
        assert response == "SOME MD WITH JSON"
        return {"parsed": True}

    monkeypatch.setattr(llms, "Config", FakeConfig)
    monkeypatch.setattr(llms, "convert_openai_messages", fake_convert_openai_messages)
    monkeypatch.setattr(llms, "create_chat_completion", fake_create_chat_completion)
    # Patch the json_repair object to expose the loads attribute
    monkeypatch.setattr(llms, "json_repair", SimpleNamespace(loads=fake_loads))
    monkeypatch.setattr(llms, "parse_json_markdown", fake_parse_json_markdown)

    # Act
    result = asyncio.run(llms.call_model(prompt=[{"role": "user", "content": "x"}], model="m", response_format="json"))

    # Assert
    assert result == {"parsed": True}


def test_call_model_logs_exception_round_113(monkeypatch, capsys):
    # Arrange: make create_chat_completion raise to exercise the except branch
    class FakeConfig:
        def __init__(self):
            self.smart_llm_provider = "p"
            self.llm_kwargs = {}

    def fake_convert_openai_messages(prompt):
        return []

    async def fake_create_chat_completion(*args, **kwargs):
        raise ValueError("boom-error")

    # Capture logger.error calls
    class FakeLogger:
        def __init__(self):
            self.last = None

        def error(self, msg):
            self.last = msg

    fake_logger = FakeLogger()

    monkeypatch.setattr(llms, "Config", FakeConfig)
    monkeypatch.setattr(llms, "convert_openai_messages", fake_convert_openai_messages)
    monkeypatch.setattr(llms, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(llms, "logger", fake_logger)

    # Act
    result = asyncio.run(llms.call_model(prompt=[{"role": "user", "content": "x"}], model="err-model", response_format=None))

    # Assert: function returns None on exception and logger.error was called with the exception message
    assert result is None
    assert fake_logger.last is not None
    assert "boom-error" in fake_logger.last
    # Also the function prints the warning triangle; ensure there is output
    captured = capsys.readouterr()
    assert "⚠️ Error in calling model" in captured.out
