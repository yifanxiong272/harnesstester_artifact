import builtins
import types
import pytest

from sweagent.agent.models import LiteLLMModel


def _make_lite_model_with_limit(per_limit: float) -> LiteLLMModel:
    """Create a LiteLLMModel instance without running __init__ and attach
    a minimal config object that exposes per_instance_cost_limit.

    Using object.__new__ avoids invoking any complex startup logic in
    __init__, letting the test deterministically set the config attribute.
    """
    m = object.__new__(LiteLLMModel)
    # simple config object with the required attribute
    cfg = types.SimpleNamespace(per_instance_cost_limit=per_limit)
    m.config = cfg
    return m


def test_instance_cost_limit_returns_config_value_round_135():
    """The instance_cost_limit property should return the underlying
    config.per_instance_cost_limit value unchanged.
    """
    model = _make_lite_model_with_limit(3.1415)
    assert isinstance(model.instance_cost_limit, float)
    assert model.instance_cost_limit == 3.1415


def test_instance_cost_limit_zero_round_135():
    """When the configured per-instance limit is zero, the property should
    return 0. This covers the documented "Returns 0 if there is no limit"
    behavior by ensuring zero is returned faithfully.
    """
    model = _make_lite_model_with_limit(0.0)
    assert model.instance_cost_limit == 0.0
