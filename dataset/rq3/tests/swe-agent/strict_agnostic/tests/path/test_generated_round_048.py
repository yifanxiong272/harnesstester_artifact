import pytest
import sweagent.agent.models as models

# Lightweight dummy classes to drive control flow in get_model without touching external systems.
class DummyGeneric:
    def __init__(self, name):
        self.name = name
    def model_dump(self):
        # return a mapping suitable for constructing specific config objects
        return {"name": self.name}

class DummyHumanConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DummyHumanThoughtConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DummyReplayConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DummyInstantEmptySubmitConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DummyHumanModel:
    def __init__(self, args, tools):
        # record what was passed for assertions
        self.args = args
        self.tools = tools

class DummyHumanThoughtModel:
    def __init__(self, args, tools):
        self.args = args
        self.tools = tools

class DummyReplayModel:
    def __init__(self, args, tools):
        self.args = args
        self.tools = tools

class DummyInstantEmptySubmitModel:
    def __init__(self, args, tools):
        self.args = args
        self.tools = tools

@pytest.fixture(autouse=True)
def _ensure_clean_monkeypatch(monkeypatch):
    # Monkeypatch the classes used by get_model to deterministic dummies for every test.
    monkeypatch.setattr(models, "GenericAPIModelConfig", DummyGeneric)
    monkeypatch.setattr(models, "HumanModelConfig", DummyHumanConfig)
    monkeypatch.setattr(models, "HumanThoughtModelConfig", DummyHumanThoughtConfig)
    monkeypatch.setattr(models, "ReplayModelConfig", DummyReplayConfig)
    monkeypatch.setattr(models, "InstantEmptySubmitModelConfig", DummyInstantEmptySubmitConfig)

    monkeypatch.setattr(models, "HumanModel", DummyHumanModel)
    monkeypatch.setattr(models, "HumanThoughtModel", DummyHumanThoughtModel)
    monkeypatch.setattr(models, "ReplayModel", DummyReplayModel)
    monkeypatch.setattr(models, "InstantEmptySubmitTestModel", DummyInstantEmptySubmitModel)
    monkeypatch.setattr(models, "LiteLLMModel", lambda args, tools: ("litellm", args, tools))
    yield


def test_human_conversion_round_048():
    # When a GenericAPIModelConfig with name 'human' is passed, get_model should
    # convert to the HumanModelConfig then return a HumanModel instance.
    args = DummyGeneric("human")
    tools = object()

    res = models.get_model(args, tools)

    # Oracle: returned object is the dummy HumanModel and has the converted config
    assert isinstance(res, DummyHumanModel), "expected DummyHumanModel returned"
    assert isinstance(res.args, DummyHumanConfig), "args should have been converted to DummyHumanConfig"
    assert getattr(res.args, "name") == "human"
    assert res.tools is tools


def test_human_thought_conversion_round_048():
    # human_thought conversion path: conversion then return HumanThoughtModel
    args = DummyGeneric("human_thought")
    tools = object()

    res = models.get_model(args, tools)

    assert isinstance(res, DummyHumanThoughtModel), "expected DummyHumanThoughtModel returned"
    assert isinstance(res.args, DummyHumanThoughtConfig), "args should have been converted to DummyHumanThoughtConfig"
    assert getattr(res.args, "name") == "human_thought"
    assert res.tools is tools


def test_replay_conversion_round_048():
    # replay conversion path: conversion then return ReplayModel
    args = DummyGeneric("replay")
    tools = object()

    res = models.get_model(args, tools)

    assert isinstance(res, DummyReplayModel), "expected DummyReplayModel returned"
    assert isinstance(res.args, DummyReplayConfig), "args should have been converted to DummyReplayConfig"
    assert getattr(res.args, "name") == "replay"
    assert res.tools is tools
