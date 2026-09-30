import types
import pytest

from aider.coders import base_coder

# Unbound method for invocation with a custom 'self'
_method = base_coder.Coder.calculate_and_show_tokens_and_cost


def make_self():
    """Create a minimal fake Coder-like object with attributes used by the method.
    We keep state minimal and deterministic.
    """
    return types.SimpleNamespace(
        message_tokens_sent=0,
        message_tokens_received=0,
        main_model=types.SimpleNamespace(token_count=lambda x: 0, info={}),
        partial_response_content="",
        # default placeholder; tests will override as needed
        compute_costs_from_tokens=lambda *args, **kwargs: 0,
        total_cost=0.0,
        message_cost=0.0,
        usage_report=None,
    )


def test_completion_no_cache_early_return_round_069():
    # completion exists and has usage, but no cache fields and main_model.info lacks input_cost_per_token
    self = make_self()

    usage = types.SimpleNamespace(prompt_tokens=7, completion_tokens=2)
    completion = types.SimpleNamespace(usage=usage)

    # Ensure input_cost_per_token absent/falsey to take the early-return branch
    self.main_model.info = {}

    _method(self, messages=[{"role": "user", "content": "hi"}], completion=completion)

    # message_tokens_sent should have been incremented by prompt_tokens (7)
    assert self.message_tokens_sent == 7
    # message_tokens_received should have been incremented by completion_tokens (2)
    assert self.message_tokens_received == 2

    # usage_report should be set to the token report and the function should return early
    assert isinstance(self.usage_report, str)
    assert self.usage_report.startswith("Tokens:")
    assert "sent" in self.usage_report
    assert "received" in self.usage_report


def test_completion_with_cache_and_small_cost_round_069(monkeypatch):
    # completion usage contains cache_read_input_tokens and cache_creation_input_tokens
    # and input_cost_per_token present so we exercise cost-calculation path
    self = make_self()

    usage = types.SimpleNamespace(
        prompt_tokens=4,
        completion_tokens=3,
        # simulate both cache read/hit and cache creation attributes
        cache_read_input_tokens=2,
        cache_creation_input_tokens=6,
        prompt_cache_hit_tokens=0,
    )
    completion = types.SimpleNamespace(usage=usage)

    # main_model reports that input_cost_per_token exists -> continue to cost logic
    self.main_model.info = {"input_cost_per_token": True}

    # Make litellm.completion_cost raise to trigger the except: cost = 0
    def _raise_completion_cost(*args, **kwargs):
        raise RuntimeError("mocked failure")

    monkeypatch.setattr(base_coder.litellm, "completion_cost", _raise_completion_cost)

    # Provide a tiny compute_costs_from_tokens to exercise the small-magnitude formatting branch
    self.compute_costs_from_tokens = lambda prompt_tokens, completion_tokens, cache_write_tokens, cache_hit_tokens: 0.0005

    _method(self, messages=[{"role": "user", "content": "hello"}], completion=completion)

    # Both cache write and cache hit were present -> separator should be a newline between tokens and cost
    assert isinstance(self.usage_report, str)
    assert "cache write" in self.usage_report
    assert "cache hit" in self.usage_report
    assert "\n" in self.usage_report

    # numeric costs should have been added to totals
    assert pytest.approx(self.total_cost, rel=1e-9) == 0.0005
    assert pytest.approx(self.message_cost, rel=1e-9) == 0.0005

    # cost formatted portion should be present (small-magnitude formatting produces a $0.000... string)
    assert "Cost:" in self.usage_report
    assert "$0." in self.usage_report


def test_cost_formatting_branches_round_069(monkeypatch):
    # Cover the format_cost branches for zero and >=0.01 magnitudes.

    # Case A: cost resolves to 0 -> format_cost returns "0.00"
    self_a = make_self()
    usage_a = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1)
    completion_a = types.SimpleNamespace(usage=usage_a)
    self_a.main_model.info = {"input_cost_per_token": True}

    # litellm returns 0 so compute_costs_from_tokens will be used; return 0
    monkeypatch.setattr(base_coder.litellm, "completion_cost", lambda *args, **kwargs: 0)
    self_a.compute_costs_from_tokens = lambda *args, **kwargs: 0

    _method(self_a, messages=[{"role": "user", "content": "x"}], completion=completion_a)

    assert "Cost:" in self_a.usage_report
    # message and session formatted costs should show 0.00
    assert "$0.00 message" in self_a.usage_report or "$0.00" in self_a.usage_report

    # Case B: cost resolves to a value >= 0.01 -> formatted with two decimals
    self_b = make_self()
    usage_b = types.SimpleNamespace(prompt_tokens=2, completion_tokens=2)
    completion_b = types.SimpleNamespace(usage=usage_b)
    self_b.main_model.info = {"input_cost_per_token": True}

    monkeypatch.setattr(base_coder.litellm, "completion_cost", lambda *args, **kwargs: 0)
    # produce cost 1.234 -> format_cost should produce 1.23
    self_b.compute_costs_from_tokens = lambda *args, **kwargs: 1.234

    _method(self_b, messages=[{"role": "user", "content": "y"}], completion=completion_b)

    assert "Cost:" in self_b.usage_report
    assert "$1.23" in self_b.usage_report
