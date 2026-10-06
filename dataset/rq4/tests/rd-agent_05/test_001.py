from types import SimpleNamespace
from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner


def test_probe_001_tie_minimize_rejected():
    # Create instance without running __init__ to control scen precisely
    runner = object.__new__(DSCoSTEERRunner)
    # Set metric_direction to False to indicate minimization
    runner.scen = SimpleNamespace(metric_direction=False)

    # Both feedbacks have identical numeric score -> tie
    base_fb = [SimpleNamespace(score=1.0)]
    new_fb = [SimpleNamespace(score=1.0)]

    # Primary behavioral check: tie under minimization must NOT be considered improvement
    result = runner.compare_and_pick_fb(base_fb, new_fb)
    assert result is False
