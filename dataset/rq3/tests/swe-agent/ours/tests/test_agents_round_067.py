import importlib
import types

import pytest

# Import the module under test
import sweagent.agent.agents as agents_mod
from sweagent.agent.agents import DefaultAgent


class FakeTools:
    class Config:
        def __init__(self):
            # parse_function is expected to be assignable by DefaultAgent
            self.parse_function = None

    def __init__(self):
        self.config = FakeTools.Config()


class FakeTemplateConfig:
    pass


class FakeHistoryProcessor:
    pass


class FakeThoughtActionParser:
    def __init__(self):
        self.type = "thought"


class FakeActionOnlyParser:
    def __init__(self):
        self.type = "action_only"


class FakeHumanThoughtModel:
    pass


class FakeHumanModel:
    pass


class FakeActionSamplerConfig:
    def __init__(self):
        self.called = False
        self.args = None

    def get(self, model, tools):
        # Return a sentinel sampler object and record the call
        self.called = True
        self.args = (model, tools)
        return {"sampler": "sentinel"}


def test_human_thought_model_sets_thought_parser_round_067(monkeypatch):
    """When model is a HumanThoughtModel, DefaultAgent should set tools.config.parse_function to ThoughtActionParser()."""
    # Patch the module-level symbols so isinstance checks and parser construction use our fakes
    monkeypatch.setattr(agents_mod, "HumanThoughtModel", FakeHumanThoughtModel, raising=False)
    monkeypatch.setattr(agents_mod, "ThoughtActionParser", FakeThoughtActionParser, raising=False)

    tools = FakeTools()
    model = FakeHumanThoughtModel()
    templates = FakeTemplateConfig()
    history_processors = [FakeHistoryProcessor()]

    agent = DefaultAgent(
        templates=templates,
        tools=tools,
        history_processors=history_processors,
        model=model,
    )

    # The branch for HumanThoughtModel should set parse_function to an instance of FakeThoughtActionParser
    assert isinstance(tools.config.parse_function, FakeThoughtActionParser), (
        "Expected tools.config.parse_function to be set to ThoughtActionParser() instance for HumanThoughtModel"
    )


def test_human_model_sets_action_only_parser_round_067(monkeypatch):
    """When model is a HumanModel, DefaultAgent should set tools.config.parse_function to ActionOnlyParser()."""
    monkeypatch.setattr(agents_mod, "HumanModel", FakeHumanModel, raising=False)
    monkeypatch.setattr(agents_mod, "ActionOnlyParser", FakeActionOnlyParser, raising=False)

    tools = FakeTools()
    model = FakeHumanModel()
    templates = FakeTemplateConfig()
    history_processors = []

    agent = DefaultAgent(
        templates=templates,
        tools=tools,
        history_processors=history_processors,
        model=model,
    )

    # The branch for HumanModel should set parse_function to an instance of FakeActionOnlyParser
    assert isinstance(tools.config.parse_function, FakeActionOnlyParser), (
        "Expected tools.config.parse_function to be set to ActionOnlyParser() instance for HumanModel"
    )


def test_action_sampler_config_get_called_and_sets_action_sampler_round_067(monkeypatch):
    """Providing an action_sampler_config should call its get(model, tools) and set _action_sampler accordingly."""
    # Ensure model is not treated as a human model to avoid interfering branches
    monkeypatch.setattr(agents_mod, "HumanModel", type("NoHuman", (), {}), raising=False)
    monkeypatch.setattr(agents_mod, "HumanThoughtModel", type("NoHumanThought", (), {}), raising=False)

    tools = FakeTools()
    model = object()
    templates = FakeTemplateConfig()
    history_processors = []

    action_sampler_config = FakeActionSamplerConfig()

    agent = DefaultAgent(
        templates=templates,
        tools=tools,
        history_processors=history_processors,
        model=model,
        action_sampler_config=action_sampler_config,
    )

    # The provided action_sampler_config.get must have been called and its return assigned
    assert action_sampler_config.called is True, "Expected action_sampler_config.get to be called"
    assert action_sampler_config.args == (model, tools), "Expected get to be called with (model, tools)"
    assert agent._action_sampler == {"sampler": "sentinel"}, (
        "Expected DefaultAgent._action_sampler to be set to the value returned by action_sampler_config.get"
    )
