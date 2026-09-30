# file: gpt_researcher/skills/curator.py:33-96
# asked: {"lines": [49, 50, 51, 52, 53, 54, 55, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 74, 75, 77, 78, 79, 80, 81, 82, 85, 87, 88, 89, 90, 91, 92, 93, 94, 96], "branches": [[50, 51], [50, 58], [77, 78], [77, 85], [89, 90], [89, 96]]}
# gained: {"lines": [49, 50, 51, 52, 53, 54, 55, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 74, 75, 77, 78, 79, 80, 81, 82, 85, 87, 88, 89, 90, 91, 92, 93, 94, 96], "branches": [[50, 51], [50, 58], [77, 78], [77, 85], [89, 90]]}

import json
import pytest

import gpt_researcher.skills.curator as curator_mod


class DummyCFG:
    def __init__(self):
        self.smart_llm_model = "test-model"
        self.smart_llm_provider = "test-provider"
        self.llm_kwargs = {}


class DummyPromptFamily:
    def curate_sources(self, query, source_data, max_results):
        return f"Curate {len(source_data)} for {query} max {max_results}"


class DummyResearcher:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.websocket = object()
        self.cfg = DummyCFG()
        self.role = "assistant-role"
        self.prompt_family = DummyPromptFamily()
        self.query = "dummy query"
        self._costs = []

    def add_costs(self, cost):
        self._costs.append(cost)


@pytest.mark.asyncio
async def test_curate_sources_success_calls_stream_output_and_parses_json(monkeypatch):
    researcher = DummyResearcher(verbose=True)
    curator = curator_mod.SourceCurator(researcher)

    source_data = [{"url": "http://a.example"}, {"url": "http://b.example"}]
    expected_curated = [{"url": "http://a.example", "score": 0.9}]

    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def fake_create_chat_completion(*, model, messages, temperature, max_tokens, llm_provider, llm_kwargs, cost_callback):
        # verify that cost callback is provided and callable
        assert callable(cost_callback)
        return json.dumps(expected_curated)

    monkeypatch.setattr(curator_mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(curator_mod, "create_chat_completion", fake_create_chat_completion)

    result = await curator.curate_sources(source_data, max_results=1)

    assert result == expected_curated
    # Expect at least pre- and post- LLM stream messages when verbose True
    assert len(stream_calls) >= 2
    assert any("Evaluating" in call[2] or "⚖️" in call[2] for call in stream_calls)
    assert any("Verified" in call[2] or "🏅" in call[2] for call in stream_calls)


@pytest.mark.asyncio
async def test_curate_sources_on_llm_exception_returns_input_and_reports_failure(monkeypatch):
    researcher = DummyResearcher(verbose=True)
    curator = curator_mod.SourceCurator(researcher)

    source_data = [{"url": "http://x.example"}]

    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def raising_create_chat_completion(*args, **kwargs):
        raise RuntimeError("llm failure")

    monkeypatch.setattr(curator_mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(curator_mod, "create_chat_completion", raising_create_chat_completion)

    result = await curator.curate_sources(source_data, max_results=5)

    assert result == source_data
    assert any("Source verification failed" in call[2] or "🚫" in call[2] for call in stream_calls)


@pytest.mark.asyncio
async def test_curate_sources_with_verbose_false_does_not_stream_but_returns_parsed(monkeypatch):
    researcher = DummyResearcher(verbose=False)
    curator = curator_mod.SourceCurator(researcher)

    source_data = [{"url": "http://c.example"}]
    expected_curated = [{"url": "http://c.example", "score": 0.5}]

    # If stream_output is called when verbose is False, fail the test
    async def should_not_be_called(*args, **kwargs):
        raise AssertionError("stream_output should not be called when verbose is False")

    async def fake_create_chat_completion(*, model, messages, temperature, max_tokens, llm_provider, llm_kwargs, cost_callback):
        return json.dumps(expected_curated)

    monkeypatch.setattr(curator_mod, "stream_output", should_not_be_called)
    monkeypatch.setattr(curator_mod, "create_chat_completion", fake_create_chat_completion)

    result = await curator.curate_sources(source_data, max_results=2)
    assert result == expected_curated
