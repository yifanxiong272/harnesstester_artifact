import pytest

from sweagent.agent.action_sampler import AskColleaguesConfig, AskColleagues


class DummyModel:
    """A minimal fake model used to pass into AskColleaguesConfig.get.
    This avoids any network or external model calls and is deterministic.
    """
    pass


class DummyTools:
    """A minimal fake tools handler used to pass into AskColleaguesConfig.get.
    """
    pass


def test_ask_colleagues_config_get_returns_instance_round_130():
    # Create the config using its defaults (pydantic BaseModel behavior)
    cfg = AskColleaguesConfig()

    # Sanity for the config default value; ensures constructor was used
    assert cfg.n_samples == 2

    model = DummyModel()
    tools = DummyTools()

    # Call the .get method under test (line intended to be covered)
    sampler = cfg.get(model, tools)

    # The returned object should be an AskColleagues instance
    assert isinstance(sampler, AskColleagues)

    # The AskColleagues instance should preserve the constructor arguments
    # by identity (not copies). This verifies the return path from .get.
    assert sampler.config is cfg
    assert sampler.model is model
    assert sampler.tools is tools


def test_ask_colleagues_config_get_creates_separate_instances_round_130():
    # Ensure multiple calls produce distinct AskColleagues instances
    cfg = AskColleaguesConfig()
    model = DummyModel()
    tools = DummyTools()

    first = cfg.get(model, tools)
    second = cfg.get(model, tools)

    # They must be different objects
    assert first is not second

    # Both should reference the same config object by identity
    assert first.config is second.config is cfg
