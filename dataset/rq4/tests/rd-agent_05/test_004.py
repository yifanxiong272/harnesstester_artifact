def test_probe_001():
    from types import SimpleNamespace
    # Import only the public entrypoint declared in the packet
    from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner

    # Local helpers (kept inside the test as required)
    def _fake_self(metric_direction: bool):
        # Minimal object with scen.metric_direction only
        return SimpleNamespace(scen=SimpleNamespace(metric_direction=metric_direction))

    def _single_fb(score):
        # Single-element sequence with an object exposing .score
        return [SimpleNamespace(score=score)]

    # Activation conditions from the boundary plan: minimization (False) and tied scores
    self_obj = _fake_self(metric_direction=False)
    base_fb = _single_fb(0.0)
    new_fb = _single_fb(0.0)

    # Obtain the unbound function object from the declared public class and call it
    compare_fn = DSCoSTEERRunner.compare_and_pick_fb
    result = compare_fn(self_obj, base_fb, new_fb)

    # Primary behavioral oracle: for minimization, ties must NOT be treated as improvements
    assert result is False, (
        "Invariant violated: under minimization (metric_direction==False), a new feedback \n"
        "with score equal to the base feedback's score should NOT be selected as an improvement.\n"
        f"compare_and_pick_fb returned {result} for equal scores (base=0.0, new=0.0)."
    )
