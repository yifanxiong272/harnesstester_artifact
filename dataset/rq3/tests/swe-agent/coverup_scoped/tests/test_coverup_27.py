# file: sweagent/agent/models.py:821-849
# asked: {"lines": [828, 830, 832, 837, 838, 840, 841], "branches": [[827, 828], [829, 830], [831, 832], [836, 837], [839, 840]]}
# gained: {"lines": [830, 832, 837, 838, 840, 841], "branches": [[829, 830], [831, 832], [836, 837], [839, 840]]}

import pytest
import types

import sweagent.agent.models as models


def _patch_model_classes(monkeypatch):
    """
    Replace model config and model classes in the module with simple fakes
    that allow isinstance checks and simple construction.
    Returns a dict of the fake classes for inspection if needed.
    """
    # Fake config base classes
    class GenericAPIModelConfigFake:
        def __init__(self, name, **kwargs):
            self.name = name
            self._data = {"name": name, **kwargs}

        def model_dump(self):
            # emulate pydantic .model_dump
            return dict(self._data)

    class HumanModelConfigFake:
        def __init__(self, name="human", **kwargs):
            self.name = name
            self._data = {"name": name, **kwargs}

    class HumanThoughtModelConfigFake:
        def __init__(self, name="human_thought", **kwargs):
            self.name = name
            self._data = {"name": name, **kwargs}

    class ReplayModelConfigFake:
        def __init__(self, name="replay", **kwargs):
            self.name = name
            self._data = {"name": name, **kwargs}

    class InstantEmptySubmitModelConfigFake:
        def __init__(self, name="instant_empty_submit", **kwargs):
            self.name = name
            self._data = {"name": name, **kwargs}

    # Fake model classes that capture the args and tools passed in
    class HumanModelFake:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

    class HumanThoughtModelFake:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

    class ReplayModelFake:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

    class InstantEmptySubmitTestModelFake:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

    class LiteLLMModelFake:
        def __init__(self, args, tools):
            self.args = args
            self.tools = tools

    # apply monkeypatches
    monkeypatch.setattr(models, "GenericAPIModelConfig", GenericAPIModelConfigFake, raising=False)
    monkeypatch.setattr(models, "HumanModelConfig", HumanModelConfigFake, raising=False)
    monkeypatch.setattr(models, "HumanThoughtModelConfig", HumanThoughtModelConfigFake, raising=False)
    monkeypatch.setattr(models, "ReplayModelConfig", ReplayModelConfigFake, raising=False)
    monkeypatch.setattr(models, "InstantEmptySubmitModelConfig", InstantEmptySubmitModelConfigFake, raising=False)

    monkeypatch.setattr(models, "HumanModel", HumanModelFake, raising=False)
    monkeypatch.setattr(models, "HumanThoughtModel", HumanThoughtModelFake, raising=False)
    monkeypatch.setattr(models, "ReplayModel", ReplayModelFake, raising=False)
    monkeypatch.setattr(models, "InstantEmptySubmitTestModel", InstantEmptySubmitTestModelFake, raising=False)
    monkeypatch.setattr(models, "LiteLLMModel", LiteLLMModelFake, raising=False)

    return {
        "GenericAPIModelConfig": GenericAPIModelConfigFake,
        "HumanModelConfig": HumanModelConfigFake,
        "HumanThoughtModelConfig": HumanThoughtModelConfigFake,
        "ReplayModelConfig": ReplayModelConfigFake,
        "InstantEmptySubmitModelConfig": InstantEmptySubmitModelConfigFake,
        "HumanModel": HumanModelFake,
        "HumanThoughtModel": HumanThoughtModelFake,
        "ReplayModel": ReplayModelFake,
        "InstantEmptySubmitTestModel": InstantEmptySubmitTestModelFake,
        "LiteLLMModel": LiteLLMModelFake,
    }


def test_generic_converts_human_thought_and_returns(monkeypatch):
    """
    This test ensures that when a GenericAPIModelConfig with name 'human_thought'
    is passed, it gets converted to HumanThoughtModelConfig and HumanThoughtModel is returned.
    This exercises the conversion branch for 'human_thought' and the final return.
    """
    fakes = _patch_model_classes(monkeypatch)

    # Create a generic config whose model_dump contains additional fields to be passed to the specific config
    gen = fakes["GenericAPIModelConfig"]("human_thought", extra="value")
    tools = object()

    result = models.get_model(gen, tools)

    # Verify returned object is the fake HumanThoughtModel and received the converted config
    assert isinstance(result, fakes["HumanThoughtModel"]), "Expected a HumanThoughtModel instance"
    assert hasattr(result, "args"), "Result should have args attribute"
    assert result.args.name == "human_thought"
    # verify that model_dump content was propagated into the specific config
    assert getattr(result.args, "_data", {}).get("extra") == "value"
    assert result.tools is tools


def test_generic_converts_replay_and_instant_and_fallback(monkeypatch):
    """
    This test exercises the 'replay' conversion branch and also checks 'instant_empty_submit' conversion.
    Additionally it checks that a non-special name ends up at LiteLLMModel.
    """
    fakes = _patch_model_classes(monkeypatch)
    tools = object()

    # replay conversion path
    gen_replay = fakes["GenericAPIModelConfig"]("replay", replay_key=123)
    res_replay = models.get_model(gen_replay, tools)
    assert isinstance(res_replay, fakes["ReplayModel"]), "Expected a ReplayModel instance"
    assert res_replay.args.name == "replay"
    assert res_replay.args._data.get("replay_key") == 123
    assert res_replay.tools is tools

    # instant_empty_submit conversion path
    gen_instant = fakes["GenericAPIModelConfig"]("instant_empty_submit", token="t")
    res_instant = models.get_model(gen_instant, tools)
    assert isinstance(res_instant, fakes["InstantEmptySubmitTestModel"]), "Expected InstantEmptySubmitTestModel instance"
    assert res_instant.args.name == "instant_empty_submit"
    assert res_instant.args._data.get("token") == "t"
    assert res_instant.tools is tools

    # a generic with a non-special name should fall back to LiteLLMModel
    gen_other = fakes["GenericAPIModelConfig"]("gpt-like", some="x")
    res_other = models.get_model(gen_other, tools)
    assert isinstance(res_other, fakes["LiteLLMModel"]), "Expected fallback LiteLLMModel instance"
    assert res_other.args.name == "gpt-like"
    assert res_other.args._data.get("some") == "x"
    assert res_other.tools is tools


def test_direct_human_and_human_thought_configs_return_correct_models(monkeypatch):
    """
    Ensure that when args is already a specific config (HumanModelConfig or HumanThoughtModelConfig),
    the function takes the corresponding branch and returns the expected model without conversion.
    This covers the assertions and returns for 'human' and 'human_thought' when already typed.
    """
    fakes = _patch_model_classes(monkeypatch)
    tools = object()

    human_cfg = fakes["HumanModelConfig"]()
    res_human = models.get_model(human_cfg, tools)
    assert isinstance(res_human, fakes["HumanModel"]), "Expected HumanModel for HumanModelConfig"
    assert res_human.args is human_cfg or getattr(res_human.args, "name", None) == "human"
    assert res_human.tools is tools

    human_thought_cfg = fakes["HumanThoughtModelConfig"]()
    res_human_thought = models.get_model(human_thought_cfg, tools)
    assert isinstance(res_human_thought, fakes["HumanThoughtModel"]), "Expected HumanThoughtModel for HumanThoughtModelConfig"
    assert res_human_thought.args is human_thought_cfg or getattr(res_human_thought.args, "name", None) == "human_thought"
    assert res_human_thought.tools is tools
