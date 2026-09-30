import pytest
from types import SimpleNamespace

from aider.history import ChatSummary


class TestChatSummary(ChatSummary):
    """
    Subclass to intercept recursive calls to summarize_real.
    The override returns a sentinel value when depth > 0 so that
    the recursion branch can be exercised without infinite recursion.
    """

    def summarize_real(self, messages, depth=0):
        if depth > 0:
            # Return a distinctive sentinel so tests can assert recursion occurred
            return [{"role": "assistant", "content": "RECURSIVE_SENTINEL"}]
        # For depth == 0, call the original implementation
        return super().summarize_real(messages, depth)


def make_instance(cls=ChatSummary):
    # Create instance without calling __init__ to allow controlled attribute setup
    inst = object.__new__(cls)
    return inst


def test_no_models_round_120():
    cs = make_instance()
    cs.models = []
    cs.max_tokens = 100
    # tokenization should not be required because we expect the ValueError early
    cs.tokenize = lambda messages: []

    with pytest.raises(ValueError):
        cs.summarize_real([{"role": "user", "content": "hi"}])


def test_return_messages_when_total_small_round_120():
    cs = make_instance()
    # Provide a non-empty models to avoid ValueError
    cs.models = [SimpleNamespace(info={})]
    cs.max_tokens = 200

    # messages and sized correspond; total tokens = 30 + 40 = 70 <= max_tokens
    messages = [
        {"role": "user", "content": "m1"},
        {"role": "assistant", "content": "m2"},
    ]
    sized = [(30, messages[0]), (40, messages[1])]
    cs.tokenize = lambda msgs: sized

    # Should return the original messages unchanged when total <= max_tokens and depth == 0
    out = cs.summarize_real(messages)
    assert out is messages or out == messages


def test_summarize_all_when_messages_small_round_120():
    cs = make_instance()
    cs.models = [SimpleNamespace(info={})]
    # Ensure total tokens > max_tokens so code continues past the early return
    cs.max_tokens = 10

    # 4 messages (== min_split), trigger summarize_all path at line ~44
    messages = [
        {"role": "user", "content": f"m{i}"} for i in range(4)
    ]

    # Token counts large enough to exceed max_tokens so earlier return is avoided
    sized = [(100, messages[i]) for i in range(4)]
    cs.tokenize = lambda msgs: sized

    called = {}

    def fake_summarize_all(msgs):
        # record what was passed and return a sentinel summary
        called['arg'] = list(msgs)
        return [{"role": "assistant", "content": "SUMMARY_ALL"}]

    cs.summarize_all = fake_summarize_all

    out = cs.summarize_real(messages)
    assert out == [{"role": "assistant", "content": "SUMMARY_ALL"}]
    # ensure summarize_all was called with the original messages
    assert 'arg' in called and called['arg'] == messages


def test_split_index_adjust_and_recurse_round_120():
    # Use the subclass that intercepts recursion to avoid infinite recursion
    cs = make_instance(TestChatSummary)

    # Configure models so that model_max_input_tokens becomes small after -512
    # This makes the head-sizing loop break early (covering the break branch at ~82->83)
    cs.models = [SimpleNamespace(info={"max_input_tokens": 200})]

    # Set overall max_tokens to cause half_max_tokens logic to split tail/head
    cs.max_tokens = 200

    # Build 9 messages (indexes 0..8). We'll use uniform small token counts so we can
    # predict split_index and exercise the while loop that adjusts split_index.
    messages = []
    for i in range(9):
        # make message dicts so identity is preserved when returned
        role = "user"
        # make one of the earlier messages an assistant so the while loop stops there
        if i == 4:
            role = "assistant"
        messages.append({"role": role, "content": f"m{i}"})

    # Each token count is 30. With max_tokens=200, half_max_tokens=100.
    # Reverse-scan will accumulate tail tokens until >= 100; this should yield
    # an initial split_index of 6, then the while loop will run once (messages[5] not assistant)
    # and stop at messages[4] which is assistant => final split_index 5 (> min_split)
    sized = [(30, messages[i]) for i in range(len(messages))]
    cs.tokenize = lambda msgs: sized

    # Force summarize_all to return a 'summary' whose token_count is 100
    def fake_summarize_all(msgs):
        # summary content depends on keep; return identifiable list
        return [{"role": "assistant", "content": "HEAD_SUMMARY"}]

    cs.summarize_all = fake_summarize_all

    # token_count should report 100 for the summary to make summary_tokens + tail_tokens >= max_tokens
    # tail_tokens = tokens for sized[split_index:] = indices 5..8 -> 4 * 30 = 120
    # summary_tokens (100) + tail_tokens (120) = 220 >= max_tokens (200) => recursion branch
    cs.token_count = lambda msgs: 100

    # Call and expect the subclass to intercept the recursive call and return the sentinel
    out = cs.summarize_real(messages)

    assert out == [{"role": "assistant", "content": "RECURSIVE_SENTINEL"}]
