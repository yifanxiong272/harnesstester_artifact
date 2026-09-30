import types

import pytest

from browser_use.llm.anthropic.chat import ChatAnthropic


def _make_chat_instance():
    # Create an instance without running dataclass init/validation.
    inst = object.__new__(ChatAnthropic)
    # Ensure attributes exist; defaults set to None unless test overrides.
    inst.temperature = None
    inst.max_tokens = None
    inst.top_p = None
    inst.seed = None
    inst.thinking = None
    # Provide safe no-op validator and default helper methods; tests override as needed.
    inst._validate_thinking_config = types.MethodType(lambda self: None, inst)
    inst._get_betas_for_invoke = types.MethodType(lambda self: None, inst)
    inst._get_extra_body_for_invoke = types.MethodType(lambda self: None, inst)
    return inst


def test_all_params_set_round_110():
    inst = _make_chat_instance()

    # Set every supported top-level attribute so all branches that add keys run.
    inst.temperature = 0.123
    inst.max_tokens = 256
    inst.top_p = 0.9
    inst.seed = 999
    inst.thinking = {"mode": "fast"}

    # Helpers return concrete non-None values
    betas = [0.1, 0.2, 0.3]
    extra = {"trace": True}
    inst._get_betas_for_invoke = types.MethodType(lambda self: betas, inst)
    inst._get_extra_body_for_invoke = types.MethodType(lambda self: extra, inst)

    params = inst._get_client_params_for_invoke()

    # Assert all keys are present and values preserved exactly (deterministic)
    assert params["temperature"] == 0.123
    assert params["max_tokens"] == 256
    assert params["top_p"] == 0.9
    assert params["seed"] == 999
    assert params["thinking"] == {"mode": "fast"}
    assert params["betas"] is betas
    assert params["extra_body"] is extra


def test_no_params_when_everything_none_round_110():
    inst = _make_chat_instance()

    # Leave all attributes as None and helpers return None
    inst.temperature = None
    inst.max_tokens = None
    inst.top_p = None
    inst.seed = None
    inst.thinking = None
    inst._get_betas_for_invoke = types.MethodType(lambda self: None, inst)
    inst._get_extra_body_for_invoke = types.MethodType(lambda self: None, inst)

    params = inst._get_client_params_for_invoke()

    # Expect empty dict when nothing should be included
    assert isinstance(params, dict)
    assert params == {}


def test_partial_params_and_helpers_round_110():
    inst = _make_chat_instance()

    # Only a subset of attributes set
    inst.temperature = 0.0  # include temperature even if zero-ish
    inst.max_tokens = None
    inst.top_p = 1.0
    inst.seed = None
    inst.thinking = None

    # Betas returns None but extra_body returns a structure
    inst._get_betas_for_invoke = types.MethodType(lambda self: None, inst)
    inst._get_extra_body_for_invoke = types.MethodType(lambda self: {"foo": "bar"}, inst)

    params = inst._get_client_params_for_invoke()

    # Only temperature, top_p, and extra_body should be present
    assert "temperature" in params and params["temperature"] == 0.0
    assert "top_p" in params and params["top_p"] == 1.0
    assert "max_tokens" not in params
    assert "seed" not in params
    assert "thinking" not in params
    assert "betas" not in params
    assert params.get("extra_body") == {"foo": "bar"}
