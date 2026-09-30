import types
import pytest

from sweagent.agent import reviewer
from sweagent.agent.reviewer import ScoreRetryLoop


class DummyStats:
    """Minimal stand-in for InstanceStats with deterministic addition semantics.

    Supports sum(..., start=InstanceStats()) and addition with other DummyStats.
    """

    def __init__(self, value: int = 0):
        self.value = int(value)

    def __add__(self, other):
        if other is None:
            return DummyStats(self.value)
        if not isinstance(other, DummyStats):
            # allow addition with objects exposing .value
            try:
                other_val = int(getattr(other, "value"))
            except Exception:
                return NotImplemented
            return DummyStats(self.value + other_val)
        return DummyStats(self.value + other.value)

    # ensure right-add works for sum when start is DummyStats and items are DummyStats
    __radd__ = __add__

    def __eq__(self, other):
        return isinstance(other, DummyStats) and self.value == other.value

    def __repr__(self):
        return f"DummyStats({self.value})"


def make_submission(val: int):
    return types.SimpleNamespace(model_stats=DummyStats(val))


def make_model(stats_val: int):
    return types.SimpleNamespace(stats=DummyStats(stats_val))


def test_total_stats_with_no_submissions_round_144(monkeypatch):
    """When there are no submissions, _total_stats should equal model.stats alone.

    - Patch InstanceStats in the reviewer module to our DummyStats so the
      implementation uses deterministic addition.
    - Create a ScoreRetryLoop instance without invoking __init__ so we can
      directly control _submissions and _model.
    """
    # Patch the symbol where the function under test resolves InstanceStats
    monkeypatch.setattr(reviewer, "InstanceStats", DummyStats)

    loop = object.__new__(ScoreRetryLoop)
    # no submissions
    loop._submissions = []
    loop._model = make_model(5)

    result = loop._total_stats
    assert isinstance(result, DummyStats)
    assert result == DummyStats(5)


def test_total_stats_with_multiple_submissions_round_144(monkeypatch):
    """Sum the model_stats of all submissions and add model.stats.

    The generator expression in the implementation should be consumed and
    produce the expected aggregated result.
    """
    monkeypatch.setattr(reviewer, "InstanceStats", DummyStats)

    loop = object.__new__(ScoreRetryLoop)
    # submissions with model_stats values 1, 2, 3
    loop._submissions = [make_submission(1), make_submission(2), make_submission(3)]
    # model.stats is 10
    loop._model = make_model(10)

    result = loop._total_stats
    # expected 1+2+3 + 10 = 16
    assert isinstance(result, DummyStats)
    assert result == DummyStats(16)
