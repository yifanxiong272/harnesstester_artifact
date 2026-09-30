import asyncio
import importlib
import json
import pytest

# Tests for SourceCurator.curate_sources (round 66)
# All test functions end with _round_066 as required.

@pytest.mark.asyncio
async def test_curate_sources_success_verbose_round_066(monkeypatch):
    mod = importlib.import_module("gpt_researcher.skills.curator")

    # Capture stream_output calls
    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def fake_create_chat_completion(**kwargs):
        # Return a deterministic, valid JSON string as the LLM response
        return json.dumps(["http://a.example", "http://b.example"])

    monkeypatch.setattr(mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(mod, "create_chat_completion", fake_create_chat_completion)

    class DummyPromptFamily:
        def curate_sources(self, query, source_data, max_results):
            return f"CURATE:{query}:{len(source_data)}:{max_results}"

    class DummyCfg:
        smart_llm_model = "mdl"
        smart_llm_provider = "prov"
        llm_kwargs = {"k": "v"}

    class DummyResearcher:
        def __init__(self):
            self.verbose = True
            self.websocket = "ws"
            self.cfg = DummyCfg()
            self.role = "role"
            self.prompt_family = DummyPromptFamily()
            self.query = "q"
            self.add_costs = lambda *a, **k: None

    researcher = DummyResearcher()
    curator = mod.SourceCurator(researcher)

    source_data = ["s1", "s2"]
    result = await curator.curate_sources(source_data, max_results=5)

    # Oracle: should return JSON-deserialized list from fake_create_chat_completion
    assert result == ["http://a.example", "http://b.example"]

    # stream_output should have been called twice: initial eval and final verification
    assert len(stream_calls) == 2
    # First message should mention evaluating/curating
    assert "Evaluating" in stream_calls[0][2] or "curating" in stream_calls[0][2]
    # Second message should mention Verified and include the number of curated sources (2)
    assert "Verified and ranked top" in stream_calls[1][2]
    assert "2" in stream_calls[1][2]


@pytest.mark.asyncio
async def test_curate_sources_success_nonverbose_round_066(monkeypatch):
    mod = importlib.import_module("gpt_researcher.skills.curator")

    # If verbose is False, stream_output should not be invoked
    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def fake_create_chat_completion(**kwargs):
        return json.dumps([])

    monkeypatch.setattr(mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(mod, "create_chat_completion", fake_create_chat_completion)

    class DummyPromptFamily:
        def curate_sources(self, query, source_data, max_results):
            return "irrelevant"

    class DummyCfg:
        smart_llm_model = "m"
        smart_llm_provider = "p"
        llm_kwargs = {}

    class DummyResearcher:
        def __init__(self):
            self.verbose = False
            self.websocket = None
            self.cfg = DummyCfg()
            self.role = "r"
            self.prompt_family = DummyPromptFamily()
            self.query = "q"
            self.add_costs = lambda *a, **k: None

    researcher = DummyResearcher()
    curator = mod.SourceCurator(researcher)

    source_data = ["only"]
    result = await curator.curate_sources(source_data, max_results=1)

    # Should return empty list (from fake_create_chat_completion), and not call stream_output
    assert result == []
    assert stream_calls == []


@pytest.mark.asyncio
async def test_curate_sources_error_verbose_round_066(monkeypatch):
    mod = importlib.import_module("gpt_researcher.skills.curator")

    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def fake_create_chat_completion(**kwargs):
        raise RuntimeError("simulated llm failure")

    monkeypatch.setattr(mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(mod, "create_chat_completion", fake_create_chat_completion)

    class DummyPromptFamily:
        def curate_sources(self, query, source_data, max_results):
            return "p"

    class DummyCfg:
        smart_llm_model = "m"
        smart_llm_provider = "p"
        llm_kwargs = {}

    class DummyResearcher:
        def __init__(self):
            self.verbose = True
            self.websocket = "ws"
            self.cfg = DummyCfg()
            self.role = "role"
            self.prompt_family = DummyPromptFamily()
            self.query = "q"
            self.add_costs = lambda *a, **k: None

    researcher = DummyResearcher()
    curator = mod.SourceCurator(researcher)

    source_data = ["orig1"]
    result = await curator.curate_sources(source_data, max_results=3)

    # On exception, curate_sources should return the original source_data
    assert result is source_data or result == source_data

    # stream_output should have been called twice: initial eval and error notification
    assert len(stream_calls) == 2
    assert "Evaluating" in stream_calls[0][2] or "curating" in stream_calls[0][2]
    # Error message path should contain 'Source verification failed' text
    assert "Source verification failed" in stream_calls[1][2]


@pytest.mark.asyncio
async def test_curate_sources_error_nonverbose_round_066(monkeypatch):
    # Ensure the exception path returns source_data and does not call stream_output when verbose=False
    mod = importlib.import_module("gpt_researcher.skills.curator")

    stream_calls = []

    async def fake_stream_output(channel, topic, message, websocket):
        stream_calls.append((channel, topic, message, websocket))

    async def fake_create_chat_completion(**kwargs):
        raise ValueError("fail")

    monkeypatch.setattr(mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(mod, "create_chat_completion", fake_create_chat_completion)

    class DummyPromptFamily:
        def curate_sources(self, query, source_data, max_results):
            return "p"

    class DummyCfg:
        smart_llm_model = "m"
        smart_llm_provider = "p"
        llm_kwargs = {}

    class DummyResearcher:
        def __init__(self):
            self.verbose = False
            self.websocket = None
            self.cfg = DummyCfg()
            self.role = "role"
            self.prompt_family = DummyPromptFamily()
            self.query = "q"
            self.add_costs = lambda *a, **k: None

    researcher = DummyResearcher()
    curator = mod.SourceCurator(researcher)

    source_data = ["x"]
    result = await curator.curate_sources(source_data, max_results=1)

    # On exception and non-verbose, original source_data should be returned and no streams called
    assert result is source_data or result == source_data
    assert stream_calls == []
