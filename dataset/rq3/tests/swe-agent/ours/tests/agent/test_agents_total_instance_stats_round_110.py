import types
import pytest

from sweagent.agent.agents import RetryAgent

# Access the underlying fget of the property so we can call it with a fake self.
_total_instance_stats_fget = RetryAgent._total_instance_stats.fget


class DummyStats:
    """Lightweight stand-in for InstanceStats-like objects.

    Implements addition and equality so the property can combine two stats
    and we can make deterministic assertions about the result.
    """

    def __init__(self, value: int):
        self.value = int(value)

    def __add__(self, other):
        return DummyStats(self.value + other.value)

    def __eq__(self, other):
        return isinstance(other, DummyStats) and self.value == other.value

    def __repr__(self):
        return f"DummyStats({self.value})"


def test_total_instance_stats_returns_sum_round_110():
    # Build a fake `self` that has the attributes the property expects.
    fake_self = types.SimpleNamespace()
    fake_self._total_instance_attempt_stats = DummyStats(3)
    # _rloop must be non-None and must have `review_model_stats` attribute.
    fake_self._rloop = types.SimpleNamespace(review_model_stats=DummyStats(2))

    result = _total_instance_stats_fget(fake_self)

    # The property should add the two stats objects.
    assert result == DummyStats(5)


def test_total_instance_stats_asserts_when_rloop_none_round_110():
    # When _rloop is None the property asserts (raises AssertionError).
    fake_self = types.SimpleNamespace()
    fake_self._total_instance_attempt_stats = DummyStats(1)
    fake_self._rloop = None

    with pytest.raises(AssertionError):
        _total_instance_stats_fget(fake_self)
