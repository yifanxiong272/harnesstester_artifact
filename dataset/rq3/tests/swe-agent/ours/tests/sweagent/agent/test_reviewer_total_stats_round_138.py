import pytest

from sweagent.agent import reviewer
from sweagent.agent.reviewer import ChooserRetryLoop


class FakeInstanceStats:
    """Deterministic stand-in for the real InstanceStats used for testing.

    Behaves like a numeric accumulator: supports addition, equality, and
    exposes a .value attribute for easy assertions.
    """

    def __init__(self, value: int = 0):
        self.value = int(value)

    def __add__(self, other):
        # Support adding another FakeInstanceStats or something with .value
        if hasattr(other, "value"):
            return FakeInstanceStats(self.value + int(other.value))
        # Fallback: try numeric
        return FakeInstanceStats(self.value + int(other))

    # sum may use __radd__ when start is 0 (not used here, but safe)
    def __radd__(self, other):
        return self.__add__(other)

    def __eq__(self, other):
        return hasattr(other, "value") and int(other.value) == self.value

    def __repr__(self):
        return f"FakeInstanceStats({self.value})"


class SimpleSubmission:
    def __init__(self, stat_value: int):
        self.model_stats = FakeInstanceStats(stat_value)


def make_chooser_with_submissions(submissions):
    # Instantiate without running __init__ to avoid external dependencies
    c = object.__new__(ChooserRetryLoop)
    # directly set the internal submissions list used by _total_stats
    c._submissions = submissions
    return c


def test_total_stats_empty_round_138(monkeypatch):
    """When there are no submissions, _total_stats should return the start InstanceStats (value 0)."""
    # Patch the InstanceStats symbol in the reviewer module to our fake
    monkeypatch.setattr(reviewer, "InstanceStats", FakeInstanceStats)

    chooser = make_chooser_with_submissions([])

    total = chooser._total_stats

    # Expect the start value (0) when there are no submissions
    assert isinstance(total, FakeInstanceStats)
    assert total == FakeInstanceStats(0)
    assert total.value == 0


def test_total_stats_sum_round_138(monkeypatch):
    """Multiple submission.model_stats should be summed correctly by _total_stats."""
    monkeypatch.setattr(reviewer, "InstanceStats", FakeInstanceStats)

    subs = [SimpleSubmission(3), SimpleSubmission(5), SimpleSubmission(2)]
    chooser = make_chooser_with_submissions(subs)

    total = chooser._total_stats

    # 3 + 5 + 2 == 10
    assert isinstance(total, FakeInstanceStats)
    assert total.value == 10
    # equality implemented, so compare to an expected instance
    assert total == FakeInstanceStats(10)
