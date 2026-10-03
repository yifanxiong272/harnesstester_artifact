def test_probe_001():
    """
    Probe: Under minimization (metric_direction == False) a tied numeric score must NOT be treated as an improvement.

    We create a DSCoSTEERRunner instance without running its real __init__ (to avoid heavy setup) by using object.__new__ and setting a minimal scen stub.
    Pass two single-element lists as feedback containers; each element exposes a .score attribute with identical numeric value.
    The independent invariant (strict-inequality-improvement) expects compare_and_pick_fb to return False.
    """

    # Import the declared public entrypoint only
    from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner

    # Minimal stub objects used by the test
    class _ScenStub:
        def __init__(self, metric_direction: bool):
            # metric_direction: True means maximization, False means minimization
            self.metric_direction = metric_direction

    class _FBItem:
        def __init__(self, score):
            self.score = score

    # Deterministically construct a runner instance without invoking heavy __init__
    runner = object.__new__(DSCoSTEERRunner)
    # Attach only what's required by compare_and_pick_fb: scen.metric_direction
    runner.scen = _ScenStub(metric_direction=False)  # minimization objective

    # Create tied scores (exact equality) to exercise the equality-handling branch
    tied_score = 42.0
    base_fb = [_FBItem(tied_score)]
    new_fb = [_FBItem(tied_score)]

    # Exercise the public entrypoint and assert the independent invariant
    result = runner.compare_and_pick_fb(base_fb, new_fb)

    # Primary observable assertion: under minimization ties should NOT be improvements
    assert isinstance(result, bool), "compare_and_pick_fb should return a native bool"
    assert result is False, (
        "Detected bug: tied scores were treated as an improvement under minimization; "
        "expected False but got True"
    )
