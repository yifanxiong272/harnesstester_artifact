# file: aider/coders/base_coder.py:1994-2068
# asked: {"lines": [2001, 2002, 2003, 2004, 2006, 2008, 2009, 2011, 2012, 2014, 2026, 2028, 2032, 2033, 2051, 2054, 2064], "branches": [[2000, 2001], [2008, 2011], [2008, 2014], [2025, 2026], [2027, 2028], [2031, 2032], [2041, 2046], [2050, 2051], [2053, 2054], [2063, 2064]]}
# gained: {"lines": [2001, 2002, 2003, 2004, 2006, 2008, 2009, 2011, 2012, 2014, 2026, 2028, 2032, 2033, 2051, 2054, 2064], "branches": [[2000, 2001], [2008, 2011], [2008, 2014], [2025, 2026], [2027, 2028], [2031, 2032], [2050, 2051], [2053, 2054], [2063, 2064]]}

import types
import pytest
from types import SimpleNamespace

import aider.coders.base_coder as base_coder
from aider.coders.base_coder import Coder


def make_coder_with_main_model(info=None, token_count_return=0):
    # Create a Coder instance without running __init__ to avoid heavy side-effects.
    coder = Coder.__new__(Coder)
    if info is None:
        info = {}
    # minimal main_model with attributes the method expects
    main_model = SimpleNamespace()
    main_model.info = info
    # token_count can accept either list/dict or string; return a controlled number
    main_model.token_count = lambda x: token_count_return
    main_model.streaming = True
    main_model.reasoning_tag = None
    main_model.cache_control = False
    coder.main_model = main_model

    # initialize attributes used by the method
    coder.partial_response_content = ""
    coder.message_tokens_sent = 0
    coder.message_tokens_received = 0
    coder.message_cost = 0.0
    coder.total_cost = 0.0
    coder.usage_report = None
    return coder


def make_completion(usage_attrs: dict):
    usage = SimpleNamespace(**usage_attrs)
    return SimpleNamespace(usage=usage)


def assert_contains_tokens_parts(report: str, sent: int, received: int, cache_write=None, cache_hit=None):
    assert report.startswith("Tokens:")
    assert f"{base_coder.format_tokens(sent)} sent" in report
    assert f"{base_coder.format_tokens(received)} received." in report
    if cache_write is not None:
        assert f"{base_coder.format_tokens(cache_write)} cache write" in report
    else:
        assert "cache write" not in report
    if cache_hit is not None:
        assert f"{base_coder.format_tokens(cache_hit)} cache hit" in report
    else:
        assert "cache hit" not in report


def test_with_cache_read_and_write_early_return():
    # main_model.info missing 'input_cost_per_token' triggers early return after tokens_report
    coder = make_coder_with_main_model(info={})
    # Create completion usage with prompt_tokens, completion_tokens, cache read and write present
    completion = make_completion(
        {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_cache_hit_tokens": 0,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 7,
        }
    )

    messages = [{"role": "user", "content": "hello"}]
    coder.calculate_and_show_tokens_and_cost(messages, completion=completion)

    # message_tokens_sent should include prompt_tokens + cache_write_tokens per branch
    assert coder.message_tokens_sent == 10 + 7
    # message_tokens_received should equal completion_tokens
    assert coder.message_tokens_received == 5
    # usage_report should contain tokens and both cache write/hit info
    assert coder.usage_report is not None
    assert_contains_tokens_parts(
        coder.usage_report,
        sent=coder.message_tokens_sent,
        received=coder.message_tokens_received,
        cache_write=7,
        cache_hit=3,
    )


def test_without_cache_read_attr_early_return():
    # main_model.info missing 'input_cost_per_token' triggers early return after tokens_report
    coder = make_coder_with_main_model(info={})
    # Create completion usage with only prompt/completion tokens and no cache attributes
    completion = make_completion({"prompt_tokens": 2, "completion_tokens": 1})

    messages = [{"role": "user", "content": "test"}]
    coder.calculate_and_show_tokens_and_cost(messages, completion=completion)

    # message_tokens_sent should include only prompt_tokens per else branch
    assert coder.message_tokens_sent == 2
    assert coder.message_tokens_received == 1
    # usage_report should contain tokens but not cache info
    assert coder.usage_report is not None
    assert_contains_tokens_parts(
        coder.usage_report,
        sent=coder.message_tokens_sent,
        received=coder.message_tokens_received,
        cache_write=None,
        cache_hit=None,
    )


def test_compute_costs_results_in_zero_cost_format(monkeypatch):
    # Ensure we go past early return by providing input_cost_per_token
    coder = make_coder_with_main_model(info={"input_cost_per_token": 0.0001})
    # Provide a completion where litellm.completion_cost will be invoked and raise -> cost becomes 0
    completion = make_completion({"prompt_tokens": 4, "completion_tokens": 2})

    # Make litellm.completion_cost raise so that cost gets set to 0 and compute_costs_from_tokens is used
    def raising_cost(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(base_coder.litellm, "completion_cost", raising_cost)

    # Patch compute_costs_from_tokens to return 0 to hit format_cost(value==0)
    monkeypatch.setattr(coder, "compute_costs_from_tokens", lambda a, b, c, d: 0)

    messages = [{"role": "user", "content": "x"}]
    coder.calculate_and_show_tokens_and_cost(messages, completion=completion)

    # After run, costs remain zero and are formatted as "0.00"
    assert coder.message_cost == 0.0
    assert coder.total_cost == 0.0
    assert coder.usage_report is not None
    assert "$0.00" in coder.usage_report


def test_compute_costs_fallback_and_formatting_with_sep_newline(monkeypatch):
    # Provide input_cost_per_token to avoid early return
    coder = make_coder_with_main_model(info={"input_cost_per_token": 0.0001})
    # Create completion usage with both cache read and write tokens to trigger newline separator
    completion = make_completion(
        {"prompt_tokens": 4, "completion_tokens": 6, "cache_read_input_tokens": 2, "cache_creation_input_tokens": 3}
    )

    # Make litellm.completion_cost raise so compute_costs_from_tokens is called
    def raising_cost(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(base_coder.litellm, "completion_cost", raising_cost)

    # Return a non-zero cost small enough to be formatted with 2 decimals
    monkeypatch.setattr(coder, "compute_costs_from_tokens", lambda a, b, c, d: 1.234)

    messages = [{"role": "user", "content": "y"}]
    coder.calculate_and_show_tokens_and_cost(messages, completion=completion)

    # Costs should be updated to the computed cost
    assert pytest.approx(coder.message_cost, rel=1e-9) == 1.234
    assert pytest.approx(coder.total_cost, rel=1e-9) == 1.234
    assert coder.usage_report is not None
    # Separator between tokens report and cost report should be newline because both cache_hit and cache_write present
    assert "\nCost:" in coder.usage_report
    # Costs should be formatted to two decimal places
    assert "$1.23" in coder.usage_report
