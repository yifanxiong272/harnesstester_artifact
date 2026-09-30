import pandas as pd
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select.submit import BestValidSelector


class FakeFeedback:
    def __init__(self, decision: bool):
        self.decision = decision


class FakeExperiment:
    def __init__(self, result):
        # store whatever is needed by the selector
        self.result = result

    def __repr__(self):
        return f"FakeExperiment(result={self.result!r})"


class FakeScenario:
    def __init__(self, metric_direction: bool):
        self.metric_direction = metric_direction


class FakeTrace:
    def __init__(self, scen, hist, parents_map=None, after_init_list=None):
        # hist: list of tuples (exp, feedback)
        self.scen = scen
        self.hist = hist
        # parents_map: dict node_idx -> list_of_parents
        self._parents_map = parents_map or {}
        # optionally override experiment_and_feedback_list_after_init return
        self._after_init_list = after_init_list

    def get_parents(self, node_idx):
        return self._parents_map.get(node_idx, [])

    def experiment_and_feedback_list_after_init(self, return_type="all", search_type="all"):
        # mimic the signature used by the selector
        if self._after_init_list is not None:
            return list(self._after_init_list)
        # default: return the full history
        return list(self.hist)


def test_collect_sota_candidates_each_trace_round_031():
    # each_trace True: ensure branch that builds root_to_experiments and removes duplicates
    # Create experiments with different result shapes including a string 'tensor(...)' and a bad result
    # exp_a: numeric score 0.50, decision False
    exp_a = FakeExperiment(pd.DataFrame([0.5], index=["ensemble"]))
    fb_a = FakeFeedback(decision=False)

    # exp_b: string score that needs stripping 'tensor(0.75)', decision True
    exp_b = FakeExperiment(pd.DataFrame(["tensor(0.75)"], index=["ensemble"]))
    fb_b = FakeFeedback(decision=True)

    # exp_c: malformed result that will trigger the exception path and leave score=-inf
    exp_c = FakeExperiment("not-a-dataframe")
    fb_c = FakeFeedback(decision=False)

    # Build trace.hist ordering and parent relationships to create two roots
    hist = [(exp_a, fb_a), (exp_b, fb_b), (exp_c, fb_c)]
    # parents: node0 -> [], node1 -> [0], node2 -> [1]
    parents_map = {0: [], 1: [0], 2: [1]}

    scen = FakeScenario(metric_direction=True)  # direction_sign = 1
    trace = FakeTrace(scen=scen, hist=hist, parents_map=parents_map)

    selector = BestValidSelector(num_candidates=2, use_decision=True, each_trace=True)

    selected = selector.collect_sota_candidates(trace)

    # With use_decision=True, items with decision=True should be prioritized above numeric score.
    # Ensure we got exactly num_candidates experiments and that exp_b (decision True) is among them.
    assert isinstance(selected, list)
    assert len(selected) == 2
    assert any(s is exp_b for s in selected), "Expected the decision=True experiment to be selected"


def test_collect_sota_candidates_no_candidates_round_031():
    # each_trace False and experiment_and_feedback_list_after_init returns empty => should return None
    scen = FakeScenario(metric_direction=True)
    trace = FakeTrace(scen=scen, hist=[], after_init_list=[])

    selector = BestValidSelector(num_candidates=3, use_decision=False, each_trace=False)

    result = selector.collect_sota_candidates(trace)

    assert result is None


def test_direction_sign_negative_round_031():
    # Test metric_direction False so direction_sign = -1 changes ranking
    # Two experiments: exp_high has score 0.9, exp_low has score 0.1
    # With direction_sign = -1, effective scores become -0.9 and -0.1; sorting reverse=True should pick the less negative one (exp_low)
    exp_high = FakeExperiment(pd.DataFrame([0.9], index=["ensemble"]))
    exp_low = FakeExperiment(pd.DataFrame([0.1], index=["ensemble"]))
    fb = FakeFeedback(decision=False)  # decisions ignored because use_decision=False

    scen = FakeScenario(metric_direction=False)
    trace = FakeTrace(scen=scen, hist=[(exp_high, fb), (exp_low, fb)], after_init_list=[(exp_high, fb), (exp_low, fb)])

    selector = BestValidSelector(num_candidates=1, use_decision=False, each_trace=False)

    selected = selector.collect_sota_candidates(trace)

    # Expect the lower original score (exp_low) to be selected because direction is negative
    assert isinstance(selected, list)
    assert len(selected) == 1
    assert selected[0] is exp_low
