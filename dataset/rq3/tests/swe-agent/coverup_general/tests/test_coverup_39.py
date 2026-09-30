# file: sweagent/agent/models.py:557-597
# asked: {"lines": [566, 567, 568, 572, 575, 580, 590, 591, 592], "branches": [[565, 566], [566, 567], [566, 574], [574, 575], [579, 580], [589, 590]]}
# gained: {"lines": [566, 567, 568, 572, 575, 580, 590, 591, 592], "branches": [[565, 566], [566, 567], [574, 575], [579, 580], [589, 590]]}

import types
import pytest

import sweagent.agent.models as models
from sweagent.agent.models import LiteLLMModel, GenericAPIModelConfig
from sweagent.tools.tools import ToolConfig


class FakeLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # store message for assertions
        self.warnings.append(msg)


def _ensure_litellm_utils(monkeypatch, supports_fn=None, model_cost=None):
    """Helper to ensure models.litellm has the attributes we need and patch them."""
    # Ensure litellm exists on the module
    if not hasattr(models, "litellm") or models.litellm is None:
        monkeypatch.setattr(models, "litellm", types.SimpleNamespace(), raising=False)

    # utils.supports_function_calling
    if supports_fn is not None:
        # create utils namespace if missing
        if not hasattr(models.litellm, "utils") or models.litellm.utils is None:
            monkeypatch.setattr(models.litellm, "utils", types.SimpleNamespace(), raising=False)
        monkeypatch.setattr(models.litellm.utils, "supports_function_calling", supports_fn, raising=False)

    # model_cost mapping
    if model_cost is not None:
        monkeypatch.setattr(models.litellm, "model_cost", model_cost, raising=False)


def test_function_calling_warning_and_config_token_overrides(monkeypatch):
    fake_logger = FakeLogger()
    # Patch get_logger to return our fake logger
    monkeypatch.setattr(models, "get_logger", lambda *args, **kwargs: fake_logger, raising=False)

    # Ensure litellm utils.supports_function_calling returns False to trigger the warning branch
    _ensure_litellm_utils(monkeypatch, supports_fn=lambda model: False)

    # Create config with explicit max input/output tokens to exercise those branches (lines 575 and 580)
    cfg = GenericAPIModelConfig(name="gpt-test-model", max_input_tokens=123, max_output_tokens=456)
    tools = ToolConfig()
    # Force the use_function_calling property to True to trigger the check in __init__
    tools.use_function_calling = True

    m = LiteLLMModel(cfg, tools)

    # Verify that the config-provided values are used
    assert m.model_max_input_tokens == 123
    assert m.model_max_output_tokens == 456

    # Verify that the function-calling warning was emitted and mentions the model name
    assert any("does not support function calling" in w for w in fake_logger.warnings)
    assert any("gpt-test-model" in w for w in fake_logger.warnings)


def test_claude_3_7_sets_64k_and_warns_when_no_beta_header(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(models, "get_logger", lambda *args, **kwargs: fake_logger, raising=False)

    # Ensure litellm.model_cost exists (could be empty)
    _ensure_litellm_utils(monkeypatch, supports_fn=lambda model: True, model_cost={})

    # Create a Claude 3.7 model name and do NOT provide max_output_tokens so the special handling triggers
    cfg = GenericAPIModelConfig(
        name="claude-3-7-sonnet",
        max_input_tokens=None,
        max_output_tokens=None,
        completion_kwargs={},  # no beta header
    )
    tools = ToolConfig()
    # Ensure function calling doesn't interfere
    tools.use_function_calling = False

    m = LiteLLMModel(cfg, tools)

    # When name contains 'claude-3-7-sonnet' and no 128k header, max output tokens should be set to 64000
    assert m.model_max_output_tokens == 64000

    # And a warning about Claude 3.7 should have been emitted
    assert any("Claude 3.7 models do not support 128k context" in w for w in fake_logger.warnings)
