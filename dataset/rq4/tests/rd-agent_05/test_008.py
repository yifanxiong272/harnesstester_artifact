from types import SimpleNamespace
from rdagent.scenarios.data_science.dev.runner import DSCoSTEERRunner

class FB:
    def __init__(self, score):
        self.score = score

def test_compare_and_pick_fb_tie_minimization():
    """
    Probe whether a tied numeric score is (incorrectly) considered an improvement
    when scen.metric_direction == False (minimization). The defensible invariant
    is that a strict improvement is required for minimization: new.score < base.score.
    """
    # fake self with minimization (lower-is-better)
    fake_self = SimpleNamespace(scen=SimpleNamespace(metric_direction=False))

    # both feedbacks present and single-element sequences as expected by the method
    base_fb = [FB(1.0)]
    new_fb = [FB(1.0)]  # tie with base

    # call the declared instance method via the class (unbound) to avoid constructing real runner
    result = DSCoSTEERRunner.compare_and_pick_fb(fake_self, base_fb, new_fb)

    # Primary behavioral oracle: ties should NOT be improvements under minimization
    assert result is False
