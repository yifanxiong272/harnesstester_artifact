import types

from aider.coders.base_coder import Coder


def test_show_usage_report_no_report_round_168():
    """When usage_report is falsy, show_usage_report should return early and not
    touch totals or call io.tool_output or event.
    """
    fn = Coder.show_usage_report

    # create a minimal fake self
    fake = types.SimpleNamespace()
    fake.usage_report = None

    # set sentinel values
    fake.total_tokens_sent = 1
    fake.total_tokens_received = 2
    fake.message_tokens_sent = 3
    fake.message_tokens_received = 4
    fake.message_cost = 9.99
    fake.total_cost = 19.99

    # io and event that would raise if called (ensures they are not invoked)
    def _bad_io(x):
        raise AssertionError("io.tool_output should not be called when no usage_report")

    def _bad_event(*a, **k):
        raise AssertionError("event should not be called when no usage_report")

    fake.io = types.SimpleNamespace(tool_output=_bad_io)
    fake.event = _bad_event

    # Call the unbound method with our fake self
    fn(fake)

    # Ensure nothing changed
    assert fake.total_tokens_sent == 1
    assert fake.total_tokens_received == 2
    assert fake.message_tokens_sent == 3
    assert fake.message_tokens_received == 4
    assert fake.message_cost == 9.99
    assert fake.total_cost == 19.99


def test_show_usage_report_with_report_round_168():
    """When usage_report is present, show_usage_report should:
    - increment total_tokens_sent/received by message_tokens_sent/received
    - call io.tool_output with the usage_report
    - call event with the expected keyword payload
    - reset message_cost and message token counters to zero
    """
    fn = Coder.show_usage_report

    fake = types.SimpleNamespace()
    fake.usage_report = {"summary": "usage"}

    # initial values
    fake.total_tokens_sent = 10
    fake.total_tokens_received = 20
    fake.message_tokens_sent = 5
    fake.message_tokens_received = 7
    fake.message_cost = 1.23
    fake.total_cost = 4.56
    fake.main_model = "test-model"
    fake.edit_format = "plain"

    io_calls = []
    event_calls = []

    def tool_output(report):
        # capture the exact object passed
        io_calls.append(report)

    def event(name, **kwargs):
        event_calls.append((name, kwargs))

    fake.io = types.SimpleNamespace(tool_output=tool_output)
    fake.event = event

    # Call the method
    fn(fake)

    # Totals were incremented
    assert fake.total_tokens_sent == 10 + 5
    assert fake.total_tokens_received == 20 + 7

    # io.tool_output called with the usage_report
    assert io_calls == [{"summary": "usage"}]

    # event called once with correct name and payload keys/values
    assert len(event_calls) == 1
    name, payload = event_calls[0]
    assert name == "message_send"

    # Check payload contents
    assert payload["main_model"] == "test-model"
    assert payload["edit_format"] == "plain"
    assert payload["prompt_tokens"] == 5
    assert payload["completion_tokens"] == 7
    assert payload["total_tokens"] == 12
    # cost and total_cost should reflect values prior to reset
    assert payload["cost"] == 1.23
    assert payload["total_cost"] == 4.56

    # After reporting, message cost and token counters should be reset
    assert fake.message_cost == 0.0
    assert fake.message_tokens_sent == 0
    assert fake.message_tokens_received == 0
