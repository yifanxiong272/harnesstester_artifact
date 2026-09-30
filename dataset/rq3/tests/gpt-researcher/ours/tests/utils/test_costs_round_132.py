import pytest

from gpt_researcher.utils import costs
from gpt_researcher.utils.costs import _get_anthropic_pricing_multiplier


def test_no_request_options_round_132():
    # Covers the early-return when request_options is falsy (None or empty dict)
    assert _get_anthropic_pricing_multiplier("any-model", None) == 1.0
    assert _get_anthropic_pricing_multiplier("any-model", {}) == 1.0


def test_inference_geo_not_us_round_132():
    # request_options present but inference_geo != 'us' -> early return 1.0
    opts = {"inference_geo": "eu"}
    assert _get_anthropic_pricing_multiplier("model-name", opts) == 1.0


def test_inference_geo_us_with_matching_model_round_132(monkeypatch):
    # inference_geo == 'us' and model_name contains a pattern -> 1.1
    # Patch the module-level symbol where the code resolves it.
    monkeypatch.setattr(costs, "ANTHROPIC_US_INFERENCE_GEO_MODELS", ["special"], raising=False)
    assert _get_anthropic_pricing_multiplier("my-special-model", {"inference_geo": "us"}) == 1.1


def test_inference_geo_us_without_matching_model_round_132(monkeypatch):
    # inference_geo == 'us' but no pattern matches -> 1.0
    monkeypatch.setattr(costs, "ANTHROPIC_US_INFERENCE_GEO_MODELS", ["special"], raising=False)
    # Uppercase 'US' should be normalized by .lower()
    assert _get_anthropic_pricing_multiplier("other-model", {"inference_geo": "US"}) == 1.0
