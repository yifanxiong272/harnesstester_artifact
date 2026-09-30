import importlib
import sys
import types

import pytest


class FakeLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # store messages for inspection
        self.warnings.append(str(msg))


class SimpleTools:
    def __init__(self, use_function_calling: bool):
        self.use_function_calling = use_function_calling


class SimpleConfig:
    def __init__(self, name, max_input_tokens=None, max_output_tokens=None, completion_kwargs=None):
        self.name = name
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        # emulate dict-like completion_kwargs
        self.completion_kwargs = completion_kwargs or {}

    def model_copy(self, deep=True):
        # return a fresh copy so identity is different but attributes preserved
        return SimpleConfig(
            name=self.name,
            max_input_tokens=self.max_input_tokens,
            max_output_tokens=self.max_output_tokens,
            completion_kwargs=dict(self.completion_kwargs),
        )


def _inject_fakelitellm(supports_function_calling=True, model_cost=None):
    """Install a minimal fake `litellm` package into sys.modules.

    The tests import the real module under test after this injection so that
    litellm references inside the target module resolve to this fake.
    """
    model_cost = model_cost or {}
    litellm = types.ModuleType("litellm")

    utils = types.ModuleType("litellm.utils")
    # supports_function_calling should be callable(model_name) -> bool
    utils.supports_function_calling = lambda model: bool(supports_function_calling)

    # create nested module structure used by imports in the source
    types_pkg = types.ModuleType("litellm.types")
    types_utils = types.ModuleType("litellm.types.utils")

    # attach attributes
    litellm.utils = utils
    litellm.types = types_pkg
    types_pkg.utils = types_utils
    litellm.model_cost = model_cost

    # inject into sys.modules so imports resolve
    sys.modules["litellm"] = litellm
    sys.modules["litellm.utils"] = utils
    sys.modules["litellm.types"] = types_pkg
    sys.modules["litellm.types.utils"] = types_utils

    return litellm


def _reload_models_module():
    # import or reload the module under test so it picks up the fake litellm
    if "sweagent.agent.models" in sys.modules:
        return importlib.reload(sys.modules["sweagent.agent.models"])
    return importlib.import_module("sweagent.agent.models")


def test_function_calling_warning_round_044():
    # Case: tools.use_function_calling True and model does NOT support function calling
    # Expect: logger.warning called with a message mentioning the model name
    _inject_fakelitellm(supports_function_calling=False, model_cost={})
    models = _reload_models_module()

    # ensure get_logger returns our fake logger instance so we can inspect warnings
    models.get_logger = lambda *args, **kwargs: FakeLogger()

    cfg = SimpleConfig(name="test-model-no-fncall", max_input_tokens=None, max_output_tokens=None)
    tools = SimpleTools(use_function_calling=True)

    m = models.LiteLLMModel(cfg, tools)

    # the logger instance is attached to the model; check that a warning was recorded
    assert hasattr(m, "logger"), "model should have a logger attribute"
    # the warning must mention the model name as constructed in the source message
    warnings = getattr(m.logger, "warnings", [])
    assert any("test-model-no-fncall" in w for w in warnings), "expected warning mentioning model name"


def test_function_calling_no_warning_round_044():
    # Case: tools.use_function_calling True and model supports function calling
    # Expect: no warning produced and flow continues to subsequent checks
    _inject_fakelitellm(supports_function_calling=True, model_cost={})
    models = _reload_models_module()

    models.get_logger = lambda *args, **kwargs: FakeLogger()

    cfg = SimpleConfig(name="test-model-with-fncall", max_input_tokens=None, max_output_tokens=None)
    tools = SimpleTools(use_function_calling=True)

    m = models.LiteLLMModel(cfg, tools)

    warnings = getattr(m.logger, "warnings", [])
    assert warnings == [], "no warning should be emitted when model supports function calling"


def test_max_input_and_output_tokens_set_round_044():
    # When config specifies max_input_tokens and max_output_tokens they should be copied to model attributes
    _inject_fakelitellm(supports_function_calling=True, model_cost={})
    models = _reload_models_module()

    models.get_logger = lambda *args, **kwargs: FakeLogger()

    cfg = SimpleConfig(name="some-model", max_input_tokens=1234, max_output_tokens=4321)
    tools = SimpleTools(use_function_calling=False)

    m = models.LiteLLMModel(cfg, tools)

    assert getattr(m, "model_max_input_tokens") == 1234
    assert getattr(m, "model_max_output_tokens") == 4321


def test_claude_3_7_sets_64k_round_044():
    # Special case: model name contains 'claude-3-7-sonnet' and completion_kwargs lacks 128k header
    # Expect: model_max_output_tokens set to 64000 and a warning logged
    # Ensure model_cost doesn't provide a max_output_tokens to trigger the special handling
    _inject_fakelitellm(supports_function_calling=True, model_cost={})
    models = _reload_models_module()

    models.get_logger = lambda *args, **kwargs: FakeLogger()

    cfg = SimpleConfig(name="claude-3-7-sonnet-xyz", max_input_tokens=None, max_output_tokens=None, completion_kwargs={})
    tools = SimpleTools(use_function_calling=False)

    m = models.LiteLLMModel(cfg, tools)

    assert getattr(m, "model_max_output_tokens") == 64000
    warnings = getattr(m.logger, "warnings", [])
    assert any("Claude 3.7" in w or "Claude 3.7".lower() in w.lower() for w in warnings), "expected Claude warning"
