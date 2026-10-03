def test_probe_001_tie_rejected_under_minimization():
    from types import SimpleNamespace
    # Import only the declared entrypoint class
    from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner

    # Fake self with scen.metric_direction == False (minimization)
    fake_self = SimpleNamespace(scen=SimpleNamespace(metric_direction=False))

    # Create a deterministic tie: base and new feedback single-element lists
    base_fb = [SimpleNamespace(score=42.0)]
    new_fb = [SimpleNamespace(score=42.0)]

    # Call the unbound method with the fabricated self (direct instance-method invocation)
    result = DSCoSTEERRunner.compare_and_pick_fb(fake_self, base_fb, new_fb)

    # Primary oracle: under minimization, equal scores should NOT be considered an improvement
    assert result is False, (
        "Under minimization, a tied score should not be selected as an improvement; "
        f"got {result} for base.score={base_fb[0].score}, new.score={new_fb[0].score}"
    )
