import types
import pytest
from types import SimpleNamespace
import importlib

# Import the module under test
module_path = "pr_agent.algo.ai_handlers.langchain_ai_handler"
mod = importlib.import_module(module_path)
LangChainOpenAIHandler = mod.LangChainOpenAIHandler
openai = mod.openai

@pytest.mark.asyncio
async def test_img_path_warning_and_chatopenai_branch_round_070(monkeypatch):
    # Prepare a logger that captures warnings
    captured = {"warnings": [], "infos": [], "errors": []}

    class DummyLogger:
        def warning(self, msg):
            captured["warnings"].append(msg)
        def info(self, msg):
            captured["infos"].append(msg)
        def error(self, msg):
            captured["errors"].append(msg)

    monkeypatch.setattr(mod, "get_logger", lambda: DummyLogger())

    # Ensure Runnable and ChatOpenAI names exist in module
    # Make Runnable be a generic base (object) so isinstance checks succeed for our dummy classes
    monkeypatch.setattr(mod, "Runnable", object, raising=False)

    class FakeChatOpenAI:
        async def ainvoke(self, *, input, model=None, temperature=None):
            return SimpleNamespace(content="chatopenai response")

    # Ensure ChatOpenAI symbol exists so isinstance(llm, (ChatOpenAI, AzureChatOpenAI)) works
    monkeypatch.setattr(mod, "ChatOpenAI", FakeChatOpenAI, raising=False)
    monkeypatch.setattr(mod, "AzureChatOpenAI", type("AzureChatOpenAI", (), {}), raising=False)

    # Create handler without calling its __init__ (avoid external dependencies)
    handler = LangChainOpenAIHandler.__new__(LangChainOpenAIHandler)

    async def fake_create_chat_async(deployment_id=None):
        return FakeChatOpenAI()

    handler._create_chat_async = fake_create_chat_async

    # Call with img_path to hit the img_path warning branch (line ~71->72)
    content, finish_reason = await handler.chat_completion(
        model="gpt-test",
        system="system text",
        user="user text",
        temperature=0.3,
        img_path="/some/image.png",
    )

    assert content == "chatopenai response"
    assert finish_reason == "completed"

    # Assert the warning about image path was logged
    assert any("Image path is not supported for LangChainOpenAIHandler" in w for w in captured["warnings"]) 


@pytest.mark.asyncio
async def test_not_runnable_raises_notimplementederror_round_070(monkeypatch):
    # Prepare logger to capture error message
    errors = []
    class DummyLogger2:
        def error(self, msg):
            errors.append(msg)
        def warning(self, msg):
            pass
        def info(self, msg):
            pass

    monkeypatch.setattr(mod, "get_logger", lambda: DummyLogger2())

    # Make Runnable be a specific class so a plain object() is NOT an instance of Runnable
    class RunnableMarker:
        pass
    monkeypatch.setattr(mod, "Runnable", RunnableMarker, raising=False)

    handler = LangChainOpenAIHandler.__new__(LangChainOpenAIHandler)

    async def create_non_runnable(deployment_id=None):
        return object()  # plain object is not instance of RunnableMarker

    handler._create_chat_async = create_non_runnable

    with pytest.raises(NotImplementedError) as exc:
        await handler.chat_completion(model="m", system="s", user="u")

    # Error message should reference the type of the returned llm
    assert "does not implement the Runnable interface" in str(exc.value)
    assert any("does not implement the Runnable interface" in e for e in errors)


@pytest.mark.asyncio
async def test_simplified_ainvoke_for_other_llm_round_070(monkeypatch):
    # Capture info logs to verify simplified ainvoke branch
    infos = []
    class DummyLogger3:
        def info(self, msg):
            infos.append(msg)
        def warning(self, msg):
            pass
        def error(self, msg):
            pass

    monkeypatch.setattr(mod, "get_logger", lambda: DummyLogger3())

    # Make Runnable be object so all instances pass isinstance(llm, Runnable)
    monkeypatch.setattr(mod, "Runnable", object, raising=False)

    # Ensure ChatOpenAI and AzureChatOpenAI exist but our fake LLM will NOT be an instance of them
    monkeypatch.setattr(mod, "ChatOpenAI", type("ChatOpenAI", (), {}), raising=False)
    monkeypatch.setattr(mod, "AzureChatOpenAI", type("AzureChatOpenAI", (), {}), raising=False)

    handler = LangChainOpenAIHandler.__new__(LangChainOpenAIHandler)

    class OtherLLM:
        async def ainvoke(self, *, input):
            return SimpleNamespace(content="simple response")

    async def create_other_llm(deployment_id=None):
        return OtherLLM()

    handler._create_chat_async = create_other_llm

    content, finish_reason = await handler.chat_completion(model="ignored", system="sys", user="usr")

    assert content == "simple response"
    assert finish_reason == "completed"
    # Ensure the simplified ainvoke info log was emitted
    assert any("Using simplified ainvoke" in i for i in infos)


@pytest.mark.asyncio
async def test_rate_limit_and_api_errors_round_070(monkeypatch):
    # Test openai.RateLimitError bubbling
    handler = LangChainOpenAIHandler.__new__(LangChainOpenAIHandler)

    async def raise_rate_limit(deployment_id=None):
        raise openai.RateLimitError("too many requests")

    handler._create_chat_async = raise_rate_limit

    with pytest.raises(openai.RateLimitError):
        await handler.chat_completion(model="m", system="s", user="u")

    # Test openai.APIError bubbling
    async def raise_api_error(deployment_id=None):
        raise openai.APIError("api issue")

    handler._create_chat_async = raise_api_error

    with pytest.raises(openai.APIError):
        await handler.chat_completion(model="m", system="s", user="u")


@pytest.mark.asyncio
async def test_unknown_exception_wrapped_as_apierror_round_070(monkeypatch):
    # Unknown exception should be wrapped into openai.APIError (line ~109->111)
    handler = LangChainOpenAIHandler.__new__(LangChainOpenAIHandler)

    async def raise_unknown(deployment_id=None):
        raise ValueError("boom")

    handler._create_chat_async = raise_unknown

    with pytest.raises(openai.APIError) as excinfo:
        await handler.chat_completion(model="m", system="s", user="u")

    # The raised APIError should have the original exception as its __cause__
    assert isinstance(excinfo.value.__cause__, ValueError)
