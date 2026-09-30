# file: browser_use/beta/service.py:2161-2287
# asked: {"lines": [2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2195, 2197, 2198, 2199, 2200, 2201, 2202, 2207, 2209, 2210, 2211, 2212, 2217, 2218, 2220, 2221, 2222, 2223, 2224, 2225, 2227, 2229, 2230, 2231, 2238, 2239, 2240, 2241, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2252, 2254, 2255, 2256, 2257, 2258, 2259, 2263, 2264, 2265, 2266, 2267, 2268, 2270, 2272, 2273], "branches": [[2184, 2185], [2186, 2187], [2186, 2188], [2197, 2198], [2197, 2201], [2216, 2217], [2219, 2220], [2229, 2230], [2229, 2241], [2231, 2238], [2231, 2239], [2242, 2243], [2243, 2244], [2243, 2245], [2254, 2255], [2254, 2260], [2256, 2257], [2256, 2258], [2262, 2263], [2272, 2273], [2272, 2274], [2284, 2286]]}
# gained: {"lines": [2185, 2186, 2188, 2189, 2190, 2191, 2192, 2193, 2195, 2197, 2198, 2199, 2200, 2201, 2202, 2207, 2209, 2210, 2211, 2212, 2217, 2218, 2220, 2221, 2222, 2223, 2224, 2225, 2227, 2229, 2230, 2231, 2238, 2239, 2240, 2241, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2252, 2254, 2255, 2256, 2257, 2258, 2259, 2263, 2264, 2265, 2266, 2267, 2268, 2270, 2272, 2273], "branches": [[2184, 2185], [2186, 2188], [2197, 2198], [2197, 2201], [2216, 2217], [2219, 2220], [2229, 2230], [2229, 2241], [2231, 2238], [2231, 2239], [2242, 2243], [2243, 2244], [2243, 2245], [2254, 2255], [2256, 2257], [2256, 2258], [2262, 2263], [2272, 2273], [2272, 2274], [2284, 2286]]}

import pytest

from browser_use.beta import service


@pytest.fixture(autouse=True)
def standard_monkeypatch(monkeypatch):
    # Provide common simple implementations for helpers used by _unkeyed_tool_results
    monkeypatch.setattr(service, "_event_type", lambda ev: ev["type"])
    monkeypatch.setattr(service, "_event_payload", lambda ev: dict(ev.get("payload", {})))
    # Define delta events
    monkeypatch.setattr(
        service,
        "_TOOL_OUTPUT_DELTA_EVENTS",
        ("tool.output_delta", "exec_command.output_delta", "browser_script.output_delta"),
    )
    monkeypatch.setattr(service, "_BROWSER_SCRIPT_RESULT_EVENTS", tuple())
    # tool_output_delta_text returns whatever is in payload['delta_text']
    monkeypatch.setattr(service, "_tool_output_delta_text", lambda payload: payload.get("delta_text"))
    # command waiting payload merges payloads and stores prev for assertion
    def _command_waiting_payload(payload, previous_payload):
        merged = dict(payload or {})
        merged["merged"] = True
        merged["prev"] = previous_payload
        return merged
    monkeypatch.setattr(service, "_command_waiting_payload", _command_waiting_payload)
    # tool result text: truthy if 'text' or 'result' key present and truthy
    monkeypatch.setattr(service, "_tool_result_text", lambda payload: bool(payload.get("text") or payload.get("result")))
    yield


def test_tool_output_delta_merge_and_tool_output_replacement(monkeypatch):
    # First: two consecutive deltas with same name should merge text
    events = [
        {"type": "tool.output_delta", "payload": {"name": "n", "delta_text": "A"}},
        {"type": "tool.output_delta", "payload": {"name": "n", "delta_text": "B"}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    etype, payload = results[0]
    assert etype == "tool.output_delta"
    assert payload["name"] == "n"
    assert payload["text"] == "AB"

    # Next: a delta followed by a tool.output (non-stream) with same name should replace the delta
    events = [
        {"type": "tool.output_delta", "payload": {"name": "x", "delta_text": "first"}},
        {"type": "tool.output", "payload": {"name": "x", "text": "FINAL", "stream": False}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    etype, payload = results[0]
    assert etype == "tool.output"
    assert payload["text"] == "FINAL"

    # A tool.output with stream True should be skipped entirely
    events = [{"type": "tool.output", "payload": {"name": "s", "text": "ignored", "stream": True}}]
    results = service._unkeyed_tool_results(events)
    assert results == []


def test_command_waiting_variants(monkeypatch):
    # Case A: previous is exec_command.output_delta (not in blocked set) -> should be replaced with merged command.waiting
    events = [
        {"type": "exec_command.output_delta", "payload": {"name": "mw", "delta_text": "X"}},
        {"type": "command.waiting", "payload": {"name": "mw", "waiting": True}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    etype, payload = results[0]
    assert etype == "command.waiting"
    assert payload["merged"] is True
    # previous payload should be the previous exec_command.output_delta payload dict
    assert isinstance(payload["prev"], dict)
    assert payload["prev"]["name"] == "mw"

    # Case B: previous is tool.output (blocked), so command.waiting should be ignored (no replacement/merge)
    events = [
        {"type": "tool.output", "payload": {"name": "tb", "text": "hello"}},
        {"type": "command.waiting", "payload": {"name": "tb", "waiting": True}},
    ]
    results = service._unkeyed_tool_results(events)
    # Only the original tool.output remains
    assert len(results) == 1
    assert results[0][0] == "tool.output"
    assert results[0][1]["text"] == "hello"

    # Case C: no previous -> command.waiting payload should be created with prev None
    events = [{"type": "command.waiting", "payload": {"name": "alone"}}]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    etype, payload = results[0]
    assert etype == "command.waiting"
    assert payload["prev"] is None
    assert payload["merged"] is True


def test_exec_command_end_behaviors(monkeypatch):
    # Case A: exec_command.end with no result text -> skipped
    events = [{"type": "exec_command.end", "payload": {"name": "e1"}}]
    results = service._unkeyed_tool_results(events)
    assert results == []

    # Case B: previous is tool.output (blocked), so exec_command.end should be ignored and not replace previous
    events = [
        {"type": "tool.output", "payload": {"name": "e2", "text": "pre"}},
        {"type": "exec_command.end", "payload": {"name": "e2", "text": "endtext"}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    assert results[0][0] == "tool.output"
    assert results[0][1]["text"] == "pre"

    # Case C: previous is exec_command.output_delta (not blocked) and exec_command.end has text -> should replace previous
    events = [
        {"type": "exec_command.output_delta", "payload": {"name": "e3", "delta_text": "D"}},
        {"type": "exec_command.end", "payload": {"name": "e3", "text": "final"}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    assert results[0][0] == "exec_command.end"
    assert results[0][1]["text"] == "final"


def test_tool_failed_aborted_and_finished_variants(monkeypatch):
    # Case A: previous aborted then failed with same name -> failed should be skipped
    events = [
        {"type": "tool.aborted", "payload": {"name": "a1"}},
        {"type": "tool.failed", "payload": {"name": "a1", "reason": "x"}},
    ]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    assert results[0][0] == "tool.aborted"
    assert results[0][1]["name"] == "a1"

    # Case B: failed with no previous abort -> should be appended
    events = [{"type": "tool.failed", "payload": {"name": "b1", "reason": "y"}}]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    assert results[0][0] == "tool.failed"
    assert results[0][1]["name"] == "b1"

    # Case C: tool.finished when previous non-finished of same name exists -> finished should be skipped
    events = [
        {"type": "tool.output", "payload": {"name": "f1", "text": "t"}},
        {"type": "tool.finished", "payload": {"name": "f1"}},
    ]
    results = service._unkeyed_tool_results(events)
    # tool.finished should not have been appended, original remains
    assert len(results) == 1
    assert results[0][0] == "tool.output"

    # Case D: tool.finished with no previous -> should be appended
    events = [{"type": "tool.finished", "payload": {"name": "f2"}}]
    results = service._unkeyed_tool_results(events)
    assert len(results) == 1
    assert results[0][0] == "tool.finished"
    assert results[0][1]["name"] == "f2"
