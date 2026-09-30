import pytest

from sweagent.agent import reviewer


def test_review_model_stats_returns_instance_round_139(monkeypatch):
    """
    Verify that ChooserRetryLoop.review_model_stats constructs and returns an
    InstanceStats object as resolved from the reviewer module. We patch the
    symbol reviewer.InstanceStats so the test is deterministic and does not
    depend on the real implementation.
    """
    created = []

    class DummyInstanceStats:
        def __init__(self):
            # record creation so we can assert that a new instance is created
            self._marker = object()
            created.append(self)

    # Patch the symbol where the code under test resolves InstanceStats
    monkeypatch.setattr(reviewer, "InstanceStats", DummyInstanceStats)

    # Create ChooserRetryLoop instance without invoking its real __init__.
    # The property under test does not use instance state, so this is safe.
    loop = reviewer.ChooserRetryLoop.__new__(reviewer.ChooserRetryLoop)

    first = loop.review_model_stats
    assert isinstance(first, DummyInstanceStats)
    # subsequent access should create a fresh instance (property returns new InstanceStats())
    second = loop.review_model_stats
    assert isinstance(second, DummyInstanceStats)
    assert first is not second
    # ensure exactly two constructions happened during the test
    assert len(created) == 2
