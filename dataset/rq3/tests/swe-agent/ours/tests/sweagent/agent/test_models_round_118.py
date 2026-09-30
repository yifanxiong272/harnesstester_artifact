import pytest

from sweagent.agent import models


class ConcreteModelForTest(models.AbstractModel):
    """Concrete minimal implementation to allow instantiation of the AbstractModel."""

    def __init__(self, config=None, tools=None):
        # call the abstract base initializer (it only contains annotations)
        super().__init__(config, tools)

    def query(self, history, action_prompt="> ") -> dict:
        # Minimal deterministic implementation for tests
        return {"ok": True}


def test_reset_stats_sets_instance_stats_round_118():
    # Arrange: create concrete model instance
    m = ConcreteModelForTest(config=None, tools=None)

    # Before reset_stats, there should be no instance attribute 'stats'
    assert not hasattr(m, "stats")

    # Act: call reset_stats which should create an InstanceStats instance
    m.reset_stats()

    # Assert: stats attribute exists and is an InstanceStats instance
    assert hasattr(m, "stats")
    assert isinstance(m.stats, models.InstanceStats)


def test_instance_cost_limit_returns_zero_round_118():
    # Arrange: concrete model instance
    m = ConcreteModelForTest(config=None, tools=None)

    # The base AbstractModel.instance_cost_limit should return 0
    assert m.instance_cost_limit == 0
