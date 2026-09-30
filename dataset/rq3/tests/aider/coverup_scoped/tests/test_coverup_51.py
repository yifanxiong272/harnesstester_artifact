# file: aider/history.py:33-96
# asked: {"lines": [35, 40, 44, 61, 64, 83, 96], "branches": [[34, 35], [39, 40], [43, 44], [51, 60], [60, 61], [63, 64], [82, 83], [92, 96]]}
# gained: {"lines": [35, 40, 44, 61, 64, 83, 96], "branches": [[34, 35], [39, 40], [43, 44], [60, 61], [63, 64], [82, 83], [92, 96]]}

import types
import pytest

from types import SimpleNamespace

try:
    from aider.history import ChatSummary
except Exception:
    pytest.skip("aider.history.ChatSummary not available", allow_module_level=True)


def make_model(max_input_tokens, token_count_fn=None):
    # model object with .info dict-like and a token_count callable required by ChatSummary.__init__
    if token_count_fn is None:
        token_count_fn = lambda summary: 1
    return SimpleNamespace(info={"max_input_tokens": max_input_tokens}, token_count=token_count_fn)


def test_no_models_raises():
    # instantiate with a valid model (constructor requires at least one), then clear models to test branch
    cs = ChatSummary(models=[make_model(4000)])
    cs.models = []
    cs.max_tokens = 1000
    cs.tokenize = lambda msgs: [(1, m) for m in msgs]
    with pytest.raises(ValueError):
        cs.summarize_real([{"role": "user", "content": "hi"}])


def test_total_within_max_returns_messages():
    cs = ChatSummary(models=[make_model(4000)])
    cs.max_tokens = 100
    messages = [{"role": "user", "content": f"m{i}"} for i in range(3)]
    cs.tokenize = lambda msgs: [(1, msg) for msg in msgs]
    # ensure summarize_all/token_count are not used unexpectedly
    cs.summarize_all = lambda msgs: [{"role": "assistant", "content": "should not be used"}]
    cs.token_count = lambda summary: 0
    result = cs.summarize_real(messages)
    assert result is messages


def test_small_messages_calls_summarize_all():
    cs = ChatSummary(models=[make_model(4000)])
    cs.max_tokens = 5
    messages = [{"role": "user", "content": f"m{i}"} for i in range(4)]
    cs.tokenize = lambda msgs: [(10, msg) for msg in msgs]
    called = {}

    def fake_summarize_all(msgs):
        called['called_with'] = list(msgs)
        return [{"role": "assistant", "content": "summarized"}]

    cs.summarize_all = fake_summarize_all
    result = cs.summarize_real(messages)
    assert result == [{"role": "assistant", "content": "summarized"}]
    assert called['called_with'] == messages


def test_split_decrements_and_returns_summarize_all():
    cs = ChatSummary(models=[make_model(4000)])
    cs.max_tokens = 10
    messages = [
        {"role": "assistant", "content": "a0"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u3"},
        {"role": "user", "content": "u4"},
        {"role": "user", "content": "u5"},
    ]
    cs.tokenize = lambda msgs: [(3, msg) for msg in msgs]
    called = {}

    def fake_summarize_all(msgs):
        called['called_with'] = list(msgs)
        return [{"role": "assistant", "content": "split_summary"}]

    cs.summarize_all = fake_summarize_all
    result = cs.summarize_real(messages)
    assert result == [{"role": "assistant", "content": "split_summary"}]
    assert called['called_with'] == messages


def test_model_max_input_break_and_recursive_call():
    # model with small max_input_tokens so model_max_input_tokens becomes negative after subtracting 512
    cs = ChatSummary(models=[make_model(500)])
    cs.max_tokens = 10

    messages = [
        {"role": "assistant", "content": "a0"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u3"},
        {"role": "user", "content": "u4"},
        {"role": "assistant", "content": "a5"},
        {"role": "user", "content": "u6"},
        {"role": "user", "content": "u7"},
    ]
    sized = [(3, msg) for msg in messages]
    cs.tokenize = lambda msgs: sized

    def fake_summarize_all(msgs):
        if not msgs:
            return [{"role": "assistant", "content": "keep_summary"}]
        return [{"role": "assistant", "content": "final_summary"}]

    cs.summarize_all = fake_summarize_all

    # ensure token_count (from model) returns a large number to force recursion
    cs.token_count = lambda summary: 100

    result = cs.summarize_real(messages)
    assert result == [{"role": "assistant", "content": "final_summary"}]
