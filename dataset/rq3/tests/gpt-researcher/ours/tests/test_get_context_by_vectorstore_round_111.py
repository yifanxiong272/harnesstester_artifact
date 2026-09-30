import asyncio
import pytest
from types import SimpleNamespace

from gpt_researcher.skills import researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor

@pytest.mark.asyncio
async def test_get_context_appends_original_query_and_skips_stream_round_111(monkeypatch):
    """
    - plan_research returns two sub-queries
    - researcher.report_type != "subtopic_report" so original query should be appended
    - researcher.verbose is False so stream_output should NOT be awaited/called
    - _process_sub_query_with_vectorstore is patched to return deterministic results
    """
    calls = []

    async def fake_plan_research(self, query):
        # record invocation and return deterministic sub-queries
        calls.append(("plan_research", query))
        return ["a", "b"]

    async def fake_process_sub_query(self, sub_query, filter):
        # record invocation and return deterministic transformed result
        calls.append(("process", sub_query))
        await asyncio.sleep(0)  # ensure it's truly async
        return f"res:{sub_query}"

    async def fake_stream_output(*args, **kwargs):
        # If called when verbose is False, fail the test by recording an unexpected call
        calls.append(("stream_called_unexpectedly", args, kwargs))
        raise AssertionError("stream_output was called but researcher.verbose was False")

    # Patch the module-level stream_output where it is imported in the module under test
    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)
    # Patch instance methods on ResearchConductor
    monkeypatch.setattr(ResearchConductor, "plan_research", fake_plan_research)
    monkeypatch.setattr(ResearchConductor, "_process_sub_query_with_vectorstore", fake_process_sub_query)

    # Create a minimal researcher-like object required by the constructor
    researcher = SimpleNamespace(report_type="full_report", verbose=False, websocket="fake-ws")
    rc = ResearchConductor(researcher)

    result = await rc._get_context_by_vectorstore("query")

    # Because plan_research returned ["a","b"] and report_type != "subtopic_report",
    # the original query should be appended, and each sub_query should be processed.
    assert result == ["res:a", "res:b", "res:query"]

    # plan and process must have been called; stream should not have been called
    recorded_actions = [c[0] for c in calls]
    assert "plan_research" in recorded_actions
    # two process calls for 'a' and 'b' and one for 'query'
    process_calls = [c for c in calls if c[0] == "process"]
    assert len(process_calls) == 3
    assert not any(c[0] == "stream_called_unexpectedly" for c in calls)


@pytest.mark.asyncio
async def test_get_context_avoids_appending_and_calls_stream_when_verbose_round_111(monkeypatch):
    """
    - plan_research returns one sub-query
    - researcher.report_type == "subtopic_report" so original query should NOT be appended
    - researcher.verbose is True so stream_output should be awaited/called with expected args
    - _process_sub_query_with_vectorstore returns a deterministic result
    """
    captured = {}

    async def fake_plan_research(self, query):
        captured.setdefault("plan_calls", []).append(query)
        return ["onlyone"]

    async def fake_process_sub_query(self, sub_query, filter):
        captured.setdefault("process_calls", []).append(sub_query)
        await asyncio.sleep(0)
        return f"res:{sub_query}"

    async def fake_stream_output(channel, event, message, websocket, flag, sub_queries):
        # capture the exact payload shape passed to stream_output
        captured["stream_args"] = {
            "channel": channel,
            "event": event,
            "message": message,
            "websocket": websocket,
            "flag": flag,
            "sub_queries": sub_queries,
        }
        # return None (typical for a fire-and-forget stream helper)
        return None

    # Patch objects where the production code resolves them
    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)
    monkeypatch.setattr(ResearchConductor, "plan_research", fake_plan_research)
    monkeypatch.setattr(ResearchConductor, "_process_sub_query_with_vectorstore", fake_process_sub_query)

    researcher = SimpleNamespace(report_type="subtopic_report", verbose=True, websocket="ws-123")
    rc = ResearchConductor(researcher)

    result = await rc._get_context_by_vectorstore("orig-query")

    # Since plan_research returned ["onlyone"] and report_type == "subtopic_report",
    # original query should NOT be appended.
    assert result == ["res:onlyone"]

    # stream_output should have been called exactly once and captured
    assert "stream_args" in captured
    sa = captured["stream_args"]
    assert sa["channel"] == "logs"
    assert sa["event"] == "subqueries"
    # message should include a textual representation of the sub_queries
    assert str(sa["sub_queries"]) == str(["onlyone"]) and str(["onlyone"]) in sa["message"]
    assert sa["websocket"] == "ws-123"
    assert sa["flag"] is True

    # ensure process was called for the single sub_query
    assert captured.get("process_calls") == ["onlyone"]
