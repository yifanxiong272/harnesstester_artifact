from types import SimpleNamespace

from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner


def test_probe_001():
    # Construct instance without running DSCoSTEERRunner.__init__
    inst = object.__new__(DSCoSTEERRunner)
    # Attach a minimal scen object indicating minimization (lower-is-better)
    inst.scen = SimpleNamespace(metric_direction=False)

    # Both feedback sequences contain a single feedback-like object with equal numeric scores
    base_fb = [SimpleNamespace(score=1.0)]
    new_fb = [SimpleNamespace(score=1.0)]

    # Exercise the public entrypoint
    result = inst.compare_and_pick_fb(base_fb, new_fb)

    # Primary oracle: equal scores should NOT be treated as an improvement under minimization
    assert result is False, (
        "compare_and_pick_fb treated equal scores as an improvement under minimization; "
        f"expected False but got {result}"
    )
