# file: aider/coders/base_coder.py:1994-2068
# asked: {"lines": [2001, 2002, 2003, 2004, 2006, 2008, 2009, 2011, 2012, 2014, 2026, 2028, 2032, 2033, 2051, 2054, 2064], "branches": [[2000, 2001], [2008, 2011], [2008, 2014], [2025, 2026], [2027, 2028], [2031, 2032], [2041, 2046], [2050, 2051], [2053, 2054], [2063, 2064]]}
# gained: {"lines": [2001, 2002, 2003, 2004, 2006, 2008, 2009, 2011, 2012, 2014, 2026, 2028, 2032, 2033, 2051, 2054, 2064], "branches": [[2000, 2001], [2008, 2011], [2008, 2014], [2025, 2026], [2027, 2028], [2031, 2032], [2050, 2051], [2053, 2054], [2063, 2064]]}

import types
from types import SimpleNamespace

import pytest

from aider.coders.base_coder import Coder
from aider.utils import format_tokens


def make_coder():
    # Create a Coder instance without running __init__ to avoid heavy setup.
    coder = object.__new__(Coder)
    coder.message_tokens_sent = 0
    coder.message_tokens_received = 0
    coder.message_cost = 0.0
    coder.total_cost = 0.0
    coder.partial_response_content = ""
    coder.usage_report = None
    return coder


def test_no_completion_without_input_cost_sets_usage_report(monkeypatch):
    """
    When no completion is provided and main_model.info lacks input_cost_per_token,
    calculate_and_show_tokens_and_cost should compute token counts via main_model.token_count,
    set usage_report to the tokens report and return early.
    """
    coder = make_coder()

    # Prepare predictable token counts
    messages = ["one", "two"]
    coder.partial_response_content = "partial"

    def token_count(x):
        if x is messages:
            return 10
        if x == coder.partial_response_content:
            return 3
        # fallback
        return 0

    # main_model without input_cost_per_token so early return path is taken
    coder.main_model = SimpleNamespace(info={}, token_count=token_count)

    # Call the method
    res = coder.calculate_and_show_tokens_and_cost(messages, completion=None)

    # After call, should have updated the message token counters
    assert coder.message_tokens_sent == 10
    assert coder.message_tokens_received == 3

    # usage_report should be set to the tokens report string and method returns None
    assert res is None
    assert isinstance(coder.usage_report, str)
    assert coder.usage_report.startswith("Tokens:")
    # Should mention sent and received but not "Cost:"
    assert "sent" in coder.usage_report and "received." in coder.usage_report
    assert "Cost:" not in coder.usage_report


def test_completion_with_cache_uses_compute_costs_and_newline_separator(monkeypatch):
    """
    If completion.usage includes cache read/write attributes, message tokens sent should include
    both prompt and cache write tokens, and both cache write and cache hit tokens should be reported.
    litellm.completion_cost will be forced to 0 so compute_costs_from_tokens is used to get a positive cost.
    Sep should be newline when both cache_hit_tokens and cache_write_tokens are present.
    """
    coder = make_coder()

    # Prepare usage values
    usage = SimpleNamespace(
        prompt_tokens=12,
        completion_tokens=7,
        # prompt_cache_hit_tokens absent; cache_read_input_tokens present -> used for cache_hit_tokens
        cache_read_input_tokens=2,
        cache_creation_input_tokens=5,
    )
    completion = SimpleNamespace(usage=usage)

    # main_model declares input_cost_per_token to avoid early return
    coder.main_model = SimpleNamespace(info={"input_cost_per_token": 0.0001}, token_count=lambda x: 0)

    # Ensure partial_response_content token_count not used here
    coder.partial_response_content = ""

    # Force litellm.completion_cost to raise so code sets cost = 0 and then compute_costs_from_tokens is called
    import aider.llm

    monkeypatch.setattr(aider.llm.litellm, "completion_cost", lambda completion_response=None: (_ for _ in ()).throw(Exception("boom")))

    # Provide compute_costs_from_tokens returning a non-zero value to exercise non-zero formatting branch
    def compute_costs(prompt_tokens, completion_tokens, cache_write_tokens, cache_hit_tokens):
        # Check received values are as expected
        assert prompt_tokens == usage.prompt_tokens
        assert completion_tokens == usage.completion_tokens
        assert cache_write_tokens == usage.cache_creation_input_tokens
        assert cache_hit_tokens == usage.cache_read_input_tokens
        return 0.123  # non-zero cost to hit the >=0.01 branch

    # Attach method to instance
    coder.compute_costs_from_tokens = compute_costs

    # Initial message token counters
    coder.message_tokens_sent = 1
    coder.message_tokens_received = 0

    # Call the method
    coder.calculate_and_show_tokens_and_cost(messages=None, completion=completion)

    # message_tokens_sent should have increased by prompt_tokens + cache_write_tokens
    assert coder.message_tokens_sent == 1 + usage.prompt_tokens + usage.cache_creation_input_tokens
    # message_tokens_received should have increased by completion_tokens
    assert coder.message_tokens_received == usage.completion_tokens

    # total_cost and message_cost should be incremented by returned cost
    assert pytest.approx(coder.total_cost, rel=1e-6) == 0.123
    assert pytest.approx(coder.message_cost, rel=1e-6) == 0.123

    # usage_report should include cache write and cache hit tokens and contain a newline before Cost:
    assert ", " + format_tokens(usage.cache_creation_input_tokens) + " cache write" in coder.usage_report
    assert ", " + format_tokens(usage.cache_read_input_tokens) + " cache hit" in coder.usage_report
    assert "\n" in coder.usage_report.split("Cost:")[0]  # newline present before cost report
    # Costs formatted to two decimals for values >= 0.01
    assert f"${coder.message_cost:.2f}" in coder.usage_report
    assert f"${coder.total_cost:.2f}" in coder.usage_report


def test_completion_without_cache_and_zero_cost_formats_zero(monkeypatch):
    """
    If completion.usage lacks cache attributes, only prompt tokens_sent are added.
    If litellm.completion_cost returns 0 and compute_costs_from_tokens returns 0,
    format_cost should produce "0.00".
    """
    coder = make_coder()

    usage = SimpleNamespace(
        prompt_tokens=4,
        completion_tokens=6,
        # No cache_read_input_tokens or cache_creation_input_tokens attributes
    )
    completion = SimpleNamespace(usage=usage)

    # main_model provides input_cost_per_token to continue to cost logic
    coder.main_model = SimpleNamespace(info={"input_cost_per_token": 1}, token_count=lambda x: 0)
    coder.partial_response_content = ""

    # litellm.completion_cost returns 0 (no exception)
    import aider.llm

    monkeypatch.setattr(aider.llm.litellm, "completion_cost", lambda completion_response=None: 0)

    # compute_costs_from_tokens returns 0 to exercise zero formatting
    coder.compute_costs_from_tokens = lambda p, c, w, h: 0

    # Call the method
    coder.message_tokens_sent = 0
    coder.message_tokens_received = 0
    coder.total_cost = 0.0
    coder.message_cost = 0.0

    coder.calculate_and_show_tokens_and_cost(messages=None, completion=completion)

    # Only prompt tokens should have been added to sent; no cache write
    assert coder.message_tokens_sent == usage.prompt_tokens
    assert coder.message_tokens_received == usage.completion_tokens

    # Costs are zero and formatted as "0.00" in the usage_report
    assert "Cost:" in coder.usage_report
    assert "$0.00" in coder.usage_report
    # When there were no cache tokens, separator should be a single space
    assert "Tokens:" in coder.usage_report and "Cost:" in coder.usage_report
    # Ensure there's no newline between tokens report and cost report in this case
    tokens_part, cost_part = coder.usage_report.split("Cost:")
    assert "\n" not in tokens_part
