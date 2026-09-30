import builtins
import pandas as pd
import types
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select import submit
from rdagent.scenarios.data_science.proposal.exp_gen.select.submit import BestValidSelector

# Small fake helpers to emulate the minimal Trace/Experiment/Feedback shapes
class FakeExp:
    def __init__(self, result):
        # result is passed through pd.DataFrame(...) in code under test
        self.result = result

class FakeFeedback:
    def __init__(self, decision: bool):
        self.decision = decision

class FakeScen:
    def __init__(self, metric_direction: bool):
        self.metric_direction = metric_direction

class FakeTrace:
    def __init__(self, scen, hist=None, parents_map=None, ef_list=None):
        # hist: list of (exp, feedback)
        self.scen = scen
        self.hist = list(hist) if hist is not None else []
        self._parents_map = parents_map or {}
        self._ef_list = ef_list

    def get_parents(self, node_idx):
        return self._parents_map.get(node_idx, [])

    def experiment_and_feedback_list_after_init(self, return_type="all", search_type="all"):
        # mimic the signature used by the code under test
        return list(self._ef_list) if self._ef_list is not None else []


def test_collect_sota_candidates_each_trace_with_mixed_results_round_030(monkeypatch):
    """
    - each_trace = True path
    - includes: numeric result, string 'tensor(...)' result, and a result that triggers a DataFrame-construction exception
    - covers: string parsing branch, exception handling in DataFrame extraction, sorting with/without decision
    """
    # keep reference to original constructor
    original_df_ctor = pd.DataFrame

    # sentinel for making DataFrame raise
    sentinel_raise = object()

    def df_ctor(x, *args, **kwargs):
        # emulate raising only for the sentinel to trigger the except branch
        if x is sentinel_raise:
            raise ValueError("bad data for dataframe")
        return original_df_ctor(x, *args, **kwargs)

    # patch pandas.DataFrame used inside the module under test
    monkeypatch.setattr(submit, "pd", types.SimpleNamespace(**{k: getattr(pd, k) for k in dir(pd) if not k.startswith("__")}))
    monkeypatch.setattr(submit.pd, "DataFrame", df_ctor)

    # Prepare experiments
    # exp_a: numeric score 0.8 -> will be converted by DataFrame and extracted
    df_a = pd.DataFrame([[0.8]], index=["ensemble"])  # .loc['ensemble'].iloc[0] -> 0.8
    exp_a = FakeExp(df_a)
    fb_a = FakeFeedback(decision=False)

    # exp_b: string score 'tensor(0.9)' -> string branch exercised
    df_b = pd.DataFrame([["tensor(0.9)"]], index=["ensemble"])  # extraction -> 'tensor(0.9)'
    exp_b = FakeExp(df_b)
    fb_b = FakeFeedback(decision=True)

    # exp_c: will cause DataFrame(...) to raise -> exercises except branch, leaves score -inf
    exp_c = FakeExp(sentinel_raise)
    fb_c = FakeFeedback(decision=False)

    # Build hist so that sorting by get_sort_key_without_decision will place exp_b first (0.9), then exp_a, then exp_c
    hist = [(exp_a, fb_a), (exp_b, fb_b), (exp_c, fb_c)]

    # parents: node 0 has no parents, node1 parent is 0, node2 parent is 0 -> so root 0 has two exps
    parents_map = {0: [], 1: [0], 2: [0]}

    trace = FakeTrace(FakeScen(metric_direction=True), hist=hist, parents_map=parents_map)

    selector = BestValidSelector(num_candidates=2, use_decision=True, each_trace=True)

    result = selector.collect_sota_candidates(trace)

    # We expect two experiments returned. They should be the top-2 by score (0.9 and 0.8)
    assert result is not None and len(result) == 2
    # the objects themselves should be returned (order by final sort is by score descending)
    returned_ids = {id(r) for r in result}
    assert id(exp_b) in returned_ids
    assert id(exp_a) in returned_ids


def test_collect_sota_candidates_each_trace_false_no_candidates_round_030():
    """
    - each_trace = False branch
    - experiment_and_feedback_list_after_init returns empty -> should return None
    """
    trace = FakeTrace(FakeScen(metric_direction=True), hist=[], ef_list=[])
    selector = BestValidSelector(num_candidates=3, use_decision=False, each_trace=False)

    result = selector.collect_sota_candidates(trace)
    assert result is None


def test_collect_sota_candidates_direction_sign_negative_changes_order_round_030():
    """
    - Verify that when metric_direction is False (direction_sign = -1), ordering flips
      so that a lower original numeric metric is selected when selecting highest by the multiplied key
    """
    # Two experiments with numeric results 0.8 and 0.7
    df_high = pd.DataFrame([[0.8]], index=["ensemble"])  # originally higher
    df_low = pd.DataFrame([[0.7]], index=["ensemble"])   # originally lower

    exp_high = FakeExp(df_high)
    exp_low = FakeExp(df_low)
    fb_high = FakeFeedback(decision=False)
    fb_low = FakeFeedback(decision=False)

    # For each_trace=False, we rely on experiment_and_feedback_list_after_init
    ef_list = [(exp_high, fb_high), (exp_low, fb_low)]
    trace = FakeTrace(FakeScen(metric_direction=False), hist=list(ef_list), ef_list=ef_list)

    # use_decision=False so final sort uses only score (which includes the negative multiplier)
    selector = BestValidSelector(num_candidates=1, use_decision=False, each_trace=False)

    result = selector.collect_sota_candidates(trace)

    # When direction_sign is -1: keys are -0.8 and -0.7; -0.7 > -0.8, so exp_low (0.7) should be selected
    assert result is not None and len(result) == 1
    assert result[0] is exp_low
