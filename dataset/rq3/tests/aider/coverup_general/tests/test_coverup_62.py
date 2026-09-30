# file: aider/coders/base_coder.py:2102-2126
# asked: {"lines": [2106, 2107, 2109, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2124, 2125, 2126], "branches": [[2103, 2106]]}
# gained: {"lines": [2106, 2107, 2109, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2124, 2125, 2126], "branches": [[2103, 2106]]}

import pytest
from aider.coders.base_coder import Coder

def make_minimal_coder():
    # Create an instance without running __init__ to avoid heavy dependencies.
    coder = object.__new__(Coder)
    return coder

def test_show_usage_report_updates_totals_emits_event_and_resets():
    coder = make_minimal_coder()
    # Set up initial values
    coder.usage_report = "Usage: X tokens"
    coder.total_tokens_sent = 5
    coder.total_tokens_received = 7
    coder.message_tokens_sent = 3
    coder.message_tokens_received = 4
    coder.message_cost = 1.23
    coder.total_cost = 10.5
    # attributes used in event
    sentinel_model = object()
    coder.main_model = sentinel_model
    coder.edit_format = "edfmt"
    # Capture tool_output calls
    outputs = []
    class FakeIO:
        def tool_output(self, text):
            outputs.append(text)
    coder.io = FakeIO()
    # Capture event calls
    events = []
    def fake_event(name, **kwargs):
        events.append((name, kwargs))
    coder.event = fake_event

    # Call the method under test
    coder.show_usage_report()

    # Validate tool_output called with usage_report
    assert outputs == ["Usage: X tokens"]

    # Validate event called once with expected name and payload
    assert len(events) == 1
    name, payload = events[0]
    assert name == "message_send"
    assert payload["main_model"] is sentinel_model
    assert payload["edit_format"] == "edfmt"
    assert payload["prompt_tokens"] == 3
    assert payload["completion_tokens"] == 4
    assert payload["total_tokens"] == 7
    assert payload["cost"] == 1.23
    assert payload["total_cost"] == 10.5

    # Validate totals were incremented
    assert coder.total_tokens_sent == 8  # 5 + 3
    assert coder.total_tokens_received == 11  # 7 + 4

    # Validate message-level counters were reset
    assert coder.message_cost == 0.0
    assert coder.message_tokens_sent == 0
    assert coder.message_tokens_received == 0

def test_show_usage_report_noop_when_no_report():
    coder = make_minimal_coder()
    # No usage report
    coder.usage_report = ""
    # Set some values to ensure they are unchanged
    coder.total_tokens_sent = 2
    coder.total_tokens_received = 4
    coder.message_tokens_sent = 6
    coder.message_tokens_received = 8
    coder.message_cost = 0.9
    coder.total_cost = 3.3
    # Fake io and event to detect calls
    outputs = []
    class FakeIO2:
        def tool_output(self, text):
            outputs.append(text)
    coder.io = FakeIO2()
    events = []
    coder.event = lambda *a, **k: events.append((a, k))

    # Call method - should return early and not modify anything
    coder.show_usage_report()

    assert outputs == []
    assert events == []
    # Ensure nothing changed
    assert coder.total_tokens_sent == 2
    assert coder.total_tokens_received == 4
    assert coder.message_tokens_sent == 6
    assert coder.message_tokens_received == 8
    assert coder.message_cost == 0.9
    assert coder.total_cost == 3.3
