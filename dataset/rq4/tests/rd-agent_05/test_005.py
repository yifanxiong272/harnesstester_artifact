from types import SimpleNamespace

from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner


def _single_fb(score: float):
    """Return a single-element sequence with an object exposing .score."""
    return [SimpleNamespace(score=score)]


def test_probe_001():
    """
    Probe: When scen.metric_direction is False (minimization), a new feedback whose
    score equals the base feedback's score should NOT be considered an improvement.

    We call the exported entrypoint DSCoSTEERRunner.compare_and_pick_fb as an
    unbound method with a lightweight dummy self to avoid constructing the full
    runner.
    """

    # Arrange: deterministic equal scores and minimization scenario
    base_fb = _single_fb(1.0)
    new_fb = _single_fb(1.0)

    dummy_scen = SimpleNamespace(metric_direction=False)
    dummy_self = SimpleNamespace(scen=dummy_scen)

    # Act: call the public entrypoint (unbound function invocation)
    result = DSCoSTEERRunner.compare_and_pick_fb(dummy_self, base_fb, new_fb)

    # Assert: under minimization, equality must NOT be treated as improvement
    assert result is False, (
        "compare_and_pick_fb treated a tie as improvement under minimization; "
        "expected False for equal scores when scen.metric_direction is False"
    )
