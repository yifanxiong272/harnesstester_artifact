# file: sweagent/agent/models.py:599-602
# asked: {"lines": [602], "branches": []}
# gained: {"lines": [602], "branches": []}

import types
import pytest

def _make_fake_config(per_instance_cost_limit: float, name: str = "test-model"):
    class FakeConfig:
        def __init__(self):
            self.per_instance_cost_limit = per_instance_cost_limit
            self.name = name
            self.max_input_tokens = None
            self.max_output_tokens = None
            self.completion_kwargs = {}
        # pydantic's BaseModel has model_copy(deep=True). Keep signature compatible.
        def model_copy(self, deep: bool = True):
            return self
    return FakeConfig()

class _FakeTool:
    def __init__(self, use_function_calling=False):
        # LiteLLMModel checks tools.use_function_calling; keep simple attribute.
        self.use_function_calling = use_function_calling

def test_instance_cost_limit_returns_config_value(monkeypatch):
    # Import the module under test
    import sweagent.agent.models as models

    # Replace litellm with a minimal dummy module so __init__ doesn't fail
    dummy_litellm = types.SimpleNamespace(
        model_cost={},
        utils=types.SimpleNamespace(supports_function_calling=lambda model: False)
    )
    monkeypatch.setattr(models, "litellm", dummy_litellm, raising=False)

    # Create fake config with a non-default per_instance_cost_limit
    cfg = _make_fake_config(7.5, name="some-model")
    tools = _FakeTool(use_function_calling=False)

    lm = models.LiteLLMModel(cfg, tools)
    # Access property to execute the return line
    assert lm.instance_cost_limit == 7.5

    # Changing the underlying config value should be reflected on next access
    lm.config.per_instance_cost_limit = 0.0
    assert lm.instance_cost_limit == 0.0

def test_instance_cost_limit_with_zero(monkeypatch):
    import sweagent.agent.models as models

    dummy_litellm = types.SimpleNamespace(
        model_cost={},
        utils=types.SimpleNamespace(supports_function_calling=lambda model: False)
    )
    monkeypatch.setattr(models, "litellm", dummy_litellm, raising=False)

    cfg = _make_fake_config(0.0, name="another-model")
    tools = _FakeTool(use_function_calling=False)

    lm = models.LiteLLMModel(cfg, tools)
    # property should return 0.0 when configured as such
    assert lm.instance_cost_limit == 0.0
