# file: gpt_researcher/skills/curator.py:33-96
# asked: {"lines": [49, 50, 51, 52, 53, 54, 55, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 74, 75, 77, 78, 79, 80, 81, 82, 85, 87, 88, 89, 90, 91, 92, 93, 94, 96], "branches": [[50, 51], [50, 58], [77, 78], [77, 85], [89, 90], [89, 96]]}
# gained: {"lines": [49, 50, 51, 52, 53, 54, 55, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 74, 75, 77, 78, 79, 80, 81, 82, 85, 87, 88, 89, 90, 91, 92, 93, 94, 96], "branches": [[50, 51], [77, 78], [89, 90]]}

import json
from types import SimpleNamespace
import importlib
import pytest

def _load_curator_module():
    """
    Try possible module paths for the curator module to be robust across environments.
    """
    names = [
        "gpt_researcher.skills.curator",
        "gpt_researcher.gpt_researcher.skills.curator",
    ]
    last_exc = None
    for name in names:
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_exc = e
    raise last_exc


@pytest.mark.asyncio
async def test_curate_sources_success(monkeypatch):
    module = _load_curator_module()
    SourceCurator = module.SourceCurator

    calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        calls.append({"channel": channel, "tag": tag, "message": message, "websocket": websocket})

    captured_create_kwargs = {}

    async def fake_create_chat_completion(**kwargs):
        captured_create_kwargs.update(kwargs)
        return json.dumps([{"url": "http://a.example"}, {"url": "http://b.example"}])

    monkeypatch.setattr(module, "stream_output", fake_stream_output)
    monkeypatch.setattr(module, "create_chat_completion", fake_create_chat_completion)

    class DummyResearcher:
        def __init__(self):
            self.verbose = True
            self.websocket = object()
            self.cfg = SimpleNamespace(
                smart_llm_model="test-model",
                smart_llm_provider="test-provider",
                llm_kwargs={"foo": "bar"},
            )
            self.role = "system role text"
            self.query = "test query"
            self.prompt_family = SimpleNamespace(
                curate_sources=lambda query, source_data, max_results: "PROMPT_BODY"
            )

        def add_costs(self, *args, **kwargs):
            return None

    dummy = DummyResearcher()
    curator = SourceCurator(dummy)

    source_data = [{"url": "http://a.example"}, {"url": "http://b.example"}, {"url": "http://c.example"}]

    result = await curator.curate_sources(source_data, max_results=2)

    assert isinstance(result, list)
    assert result == [{"url": "http://a.example"}, {"url": "http://b.example"}]

    # Should have called stream_output before and after LLM call
    assert len(calls) == 2
    assert calls[0]["tag"] == "research_plan"
    assert "curat" in calls[0]["message"].lower() or "evaluat" in calls[0]["message"].lower()
    assert calls[1]["tag"] == "research_plan"
    assert "verif" in calls[1]["message"].lower() or "rank" in calls[1]["message"].lower()

    # create_chat_completion kwargs checks
    assert captured_create_kwargs.get("model") == "test-model"
    assert captured_create_kwargs.get("llm_provider") == "test-provider"
    messages = captured_create_kwargs.get("messages")
    assert isinstance(messages, list)
    assert any(m.get("role") == "system" and "system role text" in m.get("content", "") for m in messages)
    assert any(m.get("role") == "user" and "PROMPT_BODY" in m.get("content", "") for m in messages)


@pytest.mark.asyncio
async def test_curate_sources_llm_raises_returns_original_and_streams_error(monkeypatch):
    module = _load_curator_module()
    SourceCurator = module.SourceCurator

    calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        calls.append({"channel": channel, "tag": tag, "message": message, "websocket": websocket})

    async def fake_create_chat_completion(**kwargs):
        raise ValueError("simulated LLM failure")

    monkeypatch.setattr(module, "stream_output", fake_stream_output)
    monkeypatch.setattr(module, "create_chat_completion", fake_create_chat_completion)

    class DummyResearcher:
        def __init__(self):
            self.verbose = True
            self.websocket = object()
            self.cfg = SimpleNamespace(
                smart_llm_model="test-model-2",
                smart_llm_provider="provider-2",
                llm_kwargs={},
            )
            self.role = "role2"
            self.query = "query2"
            self.prompt_family = SimpleNamespace(
                curate_sources=lambda query, source_data, max_results: "PROMPT_X"
            )

        def add_costs(self, *args, **kwargs):
            return None

    dummy = DummyResearcher()
    curator = SourceCurator(dummy)

    source_data = [{"url": "1"}, {"url": "2"}]

    result = await curator.curate_sources(source_data, max_results=5)

    # On exception, method should return the original source_data (equal)
    assert result == source_data

    # Should have streamed once before LLM and once on exception
    assert len(calls) == 2
    assert calls[-1]["tag"] == "research_plan"
    assert "source verification failed" in calls[-1]["message"].lower() or "failed" in calls[-1]["message"].lower()
