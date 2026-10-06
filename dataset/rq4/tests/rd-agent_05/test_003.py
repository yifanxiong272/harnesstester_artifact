def test_probe_001():
    from types import SimpleNamespace
    from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner

    # Create runner instance without running __init__ to keep harness minimal.
    runner = DSCoSTEERRunner.__new__(DSCoSTEERRunner)
    # Activate minimization mode: metric_direction == False
    runner.scen = SimpleNamespace(metric_direction=False)

    # Create single-element feedback sequences with equal numeric scores (tie).
    fb_base = SimpleNamespace(score=1.0)
    fb_new = SimpleNamespace(score=1.0)
    base_fb = [fb_base]
    new_fb = [fb_new]

    # Exercise only the declared public entrypoint.
    result = runner.compare_and_pick_fb(base_fb, new_fb)

    # Primary behavioral oracle: under minimization ties must NOT be considered improvements.
    assert result is False, "Tie under minimization should not be treated as an improvement"
