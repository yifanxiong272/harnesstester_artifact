import pytest
from browser_use.beta import service as svc

# Tests exercising merging and replacement logic in _unkeyed_tool_results
# All test functions end with _round_049 as required.

def test_delta_combination_round_049(monkeypatch):
    # Arrange: make delta events and ensure delta text extraction is deterministic
    monkeypatch.setattr(svc, '_TOOL_OUTPUT_DELTA_EVENTS', ('tool.output_delta',))
    monkeypatch.setattr(svc, '_BROWSER_SCRIPT_RESULT_EVENTS', ())
    monkeypatch.setattr(svc, '_event_type', lambda e: e['mock_type'])
    monkeypatch.setattr(svc, '_event_payload', lambda e: e['payload'])
    monkeypatch.setattr(svc, '_tool_output_delta_text', lambda p: p.get('delta'))

    events = [
        {'mock_type': 'tool.output_delta', 'payload': {'name': 'alpha', 'delta': 'first-'}},
        {'mock_type': 'tool.output_delta', 'payload': {'name': 'alpha', 'delta': 'second'}}
    ]

    # Act
    results = svc._unkeyed_tool_results(events)

    # Assert: the two deltas for the same tool name are combined into a single result
    assert isinstance(results, list)
    assert len(results) == 1
    event_type, payload = results[0]
    assert event_type == 'tool.output_delta'
    # combined text should be concatenation of the two delta strings
    assert payload.get('text') == 'first-second'


def test_tool_output_replaces_previous_delta_round_049(monkeypatch):
    # Arrange: first emit a delta, then a full tool.output with same name
    monkeypatch.setattr(svc, '_TOOL_OUTPUT_DELTA_EVENTS', ('tool.output_delta',))
    monkeypatch.setattr(svc, '_BROWSER_SCRIPT_RESULT_EVENTS', ())
    monkeypatch.setattr(svc, '_event_type', lambda e: e['mock_type'])
    monkeypatch.setattr(svc, '_event_payload', lambda e: e['payload'])
    monkeypatch.setattr(svc, '_tool_output_delta_text', lambda p: p.get('delta'))

    delta_event = {'mock_type': 'tool.output_delta', 'payload': {'name': 'beta', 'delta': 'd1'}}
    tool_output_payload = {'name': 'beta', 'text': 'final-result', 'extra': 123}
    tool_output_event = {'mock_type': 'tool.output', 'payload': tool_output_payload}

    # Act
    results = svc._unkeyed_tool_results([delta_event, tool_output_event])

    # Assert: the previous delta entry should be replaced by the tool.output payload
    assert len(results) == 1
    etype, payload = results[0]
    assert etype == 'tool.output'
    # payload should equal the tool.output payload (not concatenation of deltas)
    assert payload is not None
    assert payload.get('name') == 'beta'
    assert payload.get('text') == 'final-result'
    assert payload.get('extra') == 123


def test_command_waiting_skip_and_merge_variants_round_049(monkeypatch):
    # Arrange common resolution
    monkeypatch.setattr(svc, '_event_type', lambda e: e['mock_type'])
    monkeypatch.setattr(svc, '_event_payload', lambda e: e['payload'])

    # Case A: previous result event type is in blocking set -> command.waiting must be ignored
    monkeypatch.setattr(svc, '_BROWSER_SCRIPT_RESULT_EVENTS', ())
    monkeypatch.setattr(svc, '_TOOL_OUTPUT_DELTA_EVENTS', ())

    # first event: a tool.failed for name 'cmd-block'
    tool_failed = {'mock_type': 'tool.failed', 'payload': {'name': 'cmd-block', 'text': 'failed'}}
    # then a command.waiting with same name should be skipped because previous_event_type is in block list
    cmd_waiting = {'mock_type': 'command.waiting', 'payload': {'name': 'cmd-block', 'meta': 'ignored'}}

    results = svc._unkeyed_tool_results([tool_failed, cmd_waiting])
    # Expect only the tool.failed remains, command.waiting was ignored
    assert len(results) == 1
    assert results[0][0] == 'tool.failed'
    assert results[0][1].get('name') == 'cmd-block'

    # Case B: previous result exists but is NOT in the blocking set -> command.waiting merges
    # Provide a custom _command_waiting_payload to observe the merge
    def fake_command_waiting_payload(payload, previous_payload):
        # produce a predictable merged payload for assertion
        return {'name': payload.get('name'), 'merged_text': (previous_payload.get('text') if previous_payload else '') + '|' + (payload.get('meta') or '')}

    monkeypatch.setattr(svc, '_command_waiting_payload', fake_command_waiting_payload)

    prev_other = {'mock_type': 'exec_command.output', 'payload': {'name': 'cmd-merge', 'text': 'prevtext'}}
    cmd_waiting2 = {'mock_type': 'command.waiting', 'payload': {'name': 'cmd-merge', 'meta': 'now'}}

    results2 = svc._unkeyed_tool_results([prev_other, cmd_waiting2])
    # After merging, the single result should be updated to command.waiting with merged payload
    assert len(results2) == 1
    assert results2[0][0] == 'command.waiting'
    merged_payload = results2[0][1]
    assert merged_payload.get('name') == 'cmd-merge'
    assert merged_payload.get('merged_text') == 'prevtext|now'


def test_exec_command_end_branches_and_tool_abort_finished_skip_round_049(monkeypatch):
    # Arrange generic resolvers
    monkeypatch.setattr(svc, '_event_type', lambda e: e['mock_type'])
    monkeypatch.setattr(svc, '_event_payload', lambda e: e['payload'])
    monkeypatch.setattr(svc, '_BROWSER_SCRIPT_RESULT_EVENTS', ())
    monkeypatch.setattr(svc, '_TOOL_OUTPUT_DELTA_EVENTS', ())

    # 1) exec_command.end with no text (tool result text falsy) should be skipped
    monkeypatch.setattr(svc, '_tool_result_text', lambda p, include_completion_fallback=True: '')
    e_end_no_text = {'mock_type': 'exec_command.end', 'payload': {'name': 'no-text'}}
    res = svc._unkeyed_tool_results([e_end_no_text])
    assert res == []  # skipped

    # 2) exec_command.end replaces previous result when previous_event_type is NOT in the blocking set
    # make tool_result_text truthy now
    monkeypatch.setattr(svc, '_tool_result_text', lambda p, include_completion_fallback=True: 'has')
    prev_nonblocking = {'mock_type': 'other.type', 'payload': {'name': 'replace-me', 'text': 'old'}}
    e_end_replace = {'mock_type': 'exec_command.end', 'payload': {'name': 'replace-me', 'text': 'new'}}

    res2 = svc._unkeyed_tool_results([prev_nonblocking, e_end_replace])
    # The previous element should have been replaced by exec_command.end
    assert len(res2) == 1
    assert res2[0][0] == 'exec_command.end'
    assert res2[0][1].get('name') == 'replace-me'
    assert res2[0][1].get('text') == 'new'

    # 3) exec_command.end should not replace a previous element if that previous_event_type is in the blocking set
    prev_blocking = {'mock_type': 'tool.output', 'payload': {'name': 'dont-replace', 'text': 'persist'}}
    e_end_try = {'mock_type': 'exec_command.end', 'payload': {'name': 'dont-replace', 'text': 'ignored'}}

    res3 = svc._unkeyed_tool_results([prev_blocking, e_end_try])
    # Because previous was tool.output (a member of the blocking set), exec_command.end should be ignored
    assert len(res3) == 1
    assert res3[0][0] == 'tool.output'
    assert res3[0][1].get('text') == 'persist'


def test_tool_failed_and_tool_finished_skip_when_prior_abort_or_prior_exists_round_049(monkeypatch):
    # Arrange
    monkeypatch.setattr(svc, '_event_type', lambda e: e['mock_type'])
    monkeypatch.setattr(svc, '_event_payload', lambda e: e['payload'])
    monkeypatch.setattr(svc, '_BROWSER_SCRIPT_RESULT_EVENTS', ())
    monkeypatch.setattr(svc, '_TOOL_OUTPUT_DELTA_EVENTS', ())

    # If a previous tool.aborted exists for the same name, a tool.failed should be ignored
    prev_aborted = {'mock_type': 'tool.aborted', 'payload': {'name': 'ab-me'}}
    tool_failed = {'mock_type': 'tool.failed', 'payload': {'name': 'ab-me'}}
    res = svc._unkeyed_tool_results([prev_aborted, tool_failed])
    assert len(res) == 1
    assert res[0][0] == 'tool.aborted'

    # If a previous non-finished result exists for the same name, a tool.finished should be ignored
    prev_some = {'mock_type': 'tool.output', 'payload': {'name': 'finish-me'}}
    tool_finished = {'mock_type': 'tool.finished', 'payload': {'name': 'finish-me'}}
    res2 = svc._unkeyed_tool_results([prev_some, tool_finished])
    # tool.finished should be skipped because a previous non-tool.finished with same name exists
    assert len(res2) == 1
    assert res2[0][0] == 'tool.output'
