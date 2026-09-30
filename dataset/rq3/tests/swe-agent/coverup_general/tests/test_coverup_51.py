# file: sweagent/agent/models.py:821-849
# asked: {"lines": [828, 830, 832, 837, 838, 840, 841], "branches": [[827, 828], [829, 830], [831, 832], [836, 837], [839, 840]]}
# gained: {"lines": [828, 830, 832, 837, 838, 840, 841], "branches": [[827, 828], [829, 830], [831, 832], [836, 837], [839, 840]]}

import pytest
import types

import sweagent.agent.models as models_module
from sweagent.agent.models import get_model


class _DummyGeneric:
    def __init__(self, name: str):
        self.name = name

    def model_dump(self):
        # return a dict usable to reconstruct specific config classes
        return {"name": self.name}


# Helper to create simple config and model classes
def _make_config_class(name):
    class C:
        def __init__(self, name: str):
            self.name = name

        def __repr__(self):
            return f"{name}Config(name={self.name!r})"

    C.__name__ = name + "Config"
    return C


def _make_model_class(name):
    class M:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

        def __repr__(self):
            return f"{name}Model(args={self.args!r}, tools={self.tools!r})"

    M.__name__ = name + "Model"
    return M


def _apply_monkeypatch_for_models(monkeypatch):
    """
    Monkeypatch the models module to use simple stub config/model classes so
    get_model can be tested deterministically.
    Returns a dict with the patched classes for inspection.
    """
    # Create simple config classes
    HumanModelConfig = _make_config_class("HumanModel")
    HumanThoughtModelConfig = _make_config_class("HumanThoughtModel")
    ReplayModelConfig = _make_config_class("ReplayModel")
    InstantEmptySubmitModelConfig = _make_config_class("InstantEmptySubmitModel")
    GenericAPIModelConfig = _DummyGeneric  # use the dummy generic class

    # Create simple model classes
    HumanModel = _make_model_class("Human")
    HumanThoughtModel = _make_model_class("HumanThought")
    ReplayModel = _make_model_class("Replay")
    InstantEmptySubmitTestModel = _make_model_class("InstantEmptySubmitTest")
    LiteLLMModel = _make_model_class("LiteLLM")

    # Dummy ToolConfig class (not used beyond being passed through)
    class ToolConfig:
        pass

    # Apply monkeypatches into the module under test
    monkeypatch.setattr(models_module, "HumanModelConfig", HumanModelConfig)
    monkeypatch.setattr(models_module, "HumanThoughtModelConfig", HumanThoughtModelConfig)
    monkeypatch.setattr(models_module, "ReplayModelConfig", ReplayModelConfig)
    monkeypatch.setattr(models_module, "InstantEmptySubmitModelConfig", InstantEmptySubmitModelConfig)
    monkeypatch.setattr(models_module, "GenericAPIModelConfig", GenericAPIModelConfig)

    monkeypatch.setattr(models_module, "HumanModel", HumanModel)
    monkeypatch.setattr(models_module, "HumanThoughtModel", HumanThoughtModel)
    monkeypatch.setattr(models_module, "ReplayModel", ReplayModel)
    monkeypatch.setattr(models_module, "InstantEmptySubmitTestModel", InstantEmptySubmitTestModel)
    monkeypatch.setattr(models_module, "LiteLLMModel", LiteLLMModel)

    # Patch ToolConfig import (from sweagent.tools.tools import ToolConfig)
    monkeypatch.setattr(models_module, "ToolConfig", ToolConfig)

    return {
        "HumanModelConfig": HumanModelConfig,
        "HumanThoughtModelConfig": HumanThoughtModelConfig,
        "ReplayModelConfig": ReplayModelConfig,
        "InstantEmptySubmitModelConfig": InstantEmptySubmitModelConfig,
        "GenericAPIModelConfig": GenericAPIModelConfig,
        "HumanModel": HumanModel,
        "HumanThoughtModel": HumanThoughtModel,
        "ReplayModel": ReplayModel,
        "InstantEmptySubmitTestModel": InstantEmptySubmitTestModel,
        "LiteLLMModel": LiteLLMModel,
        "ToolConfig": ToolConfig,
    }


def test_get_model_human_conversion_and_return(monkeypatch):
    patched = _apply_monkeypatch_for_models(monkeypatch)

    # Create a GenericAPIModelConfig-like instance with name "human"
    generic = _DummyGeneric("human")
    tools = object()

    model_instance = get_model(generic, tools)

    # Should return our patched HumanModel instance
    assert isinstance(model_instance, patched["HumanModel"])
    # The args passed into the model should be a HumanModelConfig instance
    assert isinstance(model_instance.args, patched["HumanModelConfig"])
    assert model_instance.args.name == "human"
    # Tools should be passed through unchanged
    assert model_instance.tools is tools


def test_get_model_human_thought_conversion_and_return(monkeypatch):
    patched = _apply_monkeypatch_for_models(monkeypatch)

    generic = _DummyGeneric("human_thought")
    tools = {"tool": "value"}

    model_instance = get_model(generic, tools)

    # Should return our patched HumanThoughtModel instance
    assert isinstance(model_instance, patched["HumanThoughtModel"])
    # The args passed into the model should be a HumanThoughtModelConfig instance
    assert isinstance(model_instance.args, patched["HumanThoughtModelConfig"])
    assert model_instance.args.name == "human_thought"
    # Tools should be passed through unchanged
    assert model_instance.tools is tools


def test_get_model_replay_conversion_and_return(monkeypatch):
    patched = _apply_monkeypatch_for_models(monkeypatch)

    generic = _DummyGeneric("replay")
    tools = ("a", "tuple")

    model_instance = get_model(generic, tools)

    # Should return our patched ReplayModel instance
    assert isinstance(model_instance, patched["ReplayModel"])
    # The args passed into the model should be a ReplayModelConfig instance
    assert isinstance(model_instance.args, patched["ReplayModelConfig"])
    assert model_instance.args.name == "replay"
    # Tools should be passed through unchanged
    assert model_instance.tools is tools
