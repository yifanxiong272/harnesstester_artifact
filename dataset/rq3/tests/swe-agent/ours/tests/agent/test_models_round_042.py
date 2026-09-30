import copy
import importlib

import pytest

from types import SimpleNamespace

# Tests target sweagent.agent.models.LiteLLMModel.__init__ behavior around
# function-calling support, max_input/output token selection, and Claude 3.7
# special-casing. We patch symbols on the module to avoid network or live
# provider calls and to make behavior deterministic.


class FakeLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # Preserve the exact text for assertions
        self.warnings.append(msg)


class FakeConfig:
    def __init__(self, name, max_input_tokens=None, max_output_tokens=None, completion_kwargs=None):
        self.name = name
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.completion_kwargs = completion_kwargs or {}

    def model_copy(self, deep=True):
        # LiteLLMModel expects a config with model_copy(deep=True) returning
        # an object with the same attributes. Use deepcopy to be faithful.
        return copy.deepcopy(self)


class FakeTools:
    def __init__(self, use_function_calling: bool):
        self.use_function_calling = use_function_calling


def setup_module_patched(module, *, supports_function_calling=None, model_cost=None):
    """Patch the target module's litellm utilities and get_logger for tests.

    Returns the FakeLogger instance that will be assigned as the model logger.
    """
    # Replace get_logger on the module so LiteLLMModel gets our FakeLogger
    fake_logger = FakeLogger()
    module.get_logger = lambda *args, **kwargs: fake_logger

    # Patch litellm.utils.supports_function_calling if provided
    if supports_function_calling is not None:
        # ensure submodule exists on the module under test
        module.litellm.utils.supports_function_calling = lambda model: supports_function_calling

    # Patch model_cost mapping used to read provider and token defaults
    if model_cost is not None:
        module.litellm.model_cost = model_cost

    return fake_logger


def test_function_calling_warning_round_042(monkeypatch):
    """When tools.use_function_calling is True but the litellm utils say the
    model does not support it, LiteLLMModel should call logger.warning with
    a message mentioning the model name and advising parse_function.
    """
    m = importlib.import_module("sweagent.agent.models")

    # Prepare deterministic environment: supports_function_calling -> False
    fake_logger = setup_module_patched(m, supports_function_calling=False, model_cost={})

    # Create a config whose name will appear in the warning
    cfg = FakeConfig(name="test-model-abc", max_input_tokens=None, max_output_tokens=10)
    tools = FakeTools(use_function_calling=True)

    # Instantiate the model (this runs the __init__ under test)
    model = m.LiteLLMModel(cfg, tools)

    # The logger attached to the instance is our FakeLogger; ensure a warning was emitted
    assert isinstance(model.logger, FakeLogger)
    assert len(model.logger.warnings) >= 1, "Expected a warning when function calling unsupported"

    first_warning = model.logger.warnings[0]
    # The warning should include the model name and mention function calling guidance
    assert "test-model-abc" in first_warning
    assert "does not support function calling" in first_warning
    assert "parse_function='thought_action'" in first_warning


def test_claude_3_7_max_output_override_round_042(monkeypatch):
    """When a Claude 3.7 model (name contains 'claude-3-7-sonnet') has no
    max_output_tokens and is missing the special 128k beta header, the model
    should get model_max_output_tokens == 64000 and emit a warning. Also
    verify that explicit max_input_tokens is respected.
    """
    m = importlib.import_module("sweagent.agent.models")

    # Ensure supports_function_calling is not exercised in this test and model_cost is empty
    fake_logger = setup_module_patched(m, supports_function_calling=True, model_cost={})

    # Set up a config that triggers the Claude 3.7 special-casing
    cfg = FakeConfig(
        name="claude-3-7-sonnet-v2",
        max_input_tokens=123,
        max_output_tokens=None,
        completion_kwargs={"extra_headers": {}}  # missing 'anthropic-beta'
    )
    tools = FakeTools(use_function_calling=False)

    model = m.LiteLLMModel(cfg, tools)

    # max_input_tokens path should set model.model_max_input_tokens directly
    assert getattr(model, "model_max_input_tokens") == 123

    # Because max_output_tokens was None and name is Claude 3.7 without beta header,
    # the implementation should overwrite model_max_output_tokens to 64000
    assert getattr(model, "model_max_output_tokens") == 64000

    # A warning should have been emitted advising about 64k default
    warnings = model.logger.warnings
    assert any("64k" in w or "64k" in w.lower() or "64,000" in w.replace(" ", "") for w in warnings), (
        "Expected a warning about setting max output tokens to 64k for Claude 3.7"
    )
