from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner


def test_probe_001():
    """Probe: under minimization (metric_direction == False), equal scores must NOT be treated as improvement.

    This test calls the entrypoint as an unbound method with a lightweight fake self and
    deterministic single-element feedback sequences so it exercises the public API
    without heavy framework setup.
    """

    # Lightweight helper types local to the test (no external deps)
    class FakeScen:
        # minimization
        metric_direction = False

    class FakeSelf:
        def __init__(self):
            self.scen = FakeScen()

    class SingleFB:
        def __init__(self, score):
            self.score = score

    def single_feedback_list(score):
        return [SingleFB(score)]

    # Deterministic, tied scores (equality case)
    fake_self = FakeSelf()
    base_fb = single_feedback_list(1.0)
    new_fb = single_feedback_list(1.0)

    # Invoke the entrypoint as an unbound method per activation guidance
    result = DSCoSTEERRunner.compare_and_pick_fb(fake_self, base_fb, new_fb)

    # Primary oracle: under minimization, ties should NOT be selected as improvement
    assert result is False, (
        "compare_and_pick_fb treated a tie as an improvement under minimization. "
        "Expected False when base.score == new.score and scen.metric_direction is False"
    )
