# file: rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py:187-260
# asked: {"lines": [189, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 221, 224, 226, 227, 228, 230, 231, 232, 233, 234, 235, 236, 237, 240, 241, 242, 243, 244, 245, 247, 249, 251, 252, 253, 256, 258, 259, 260], "branches": [[197, 198], [197, 207], [200, 201], [200, 202], [212, 213], [212, 221], [215, 216], [215, 217], [224, 226], [224, 249], [231, 232], [231, 240], [233, 231], [233, 234], [235, 236], [235, 237], [241, 242], [241, 247], [242, 243], [242, 244], [251, 252], [251, 256]]}
# gained: {"lines": [189, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 221, 224, 226, 227, 228, 230, 231, 232, 233, 234, 235, 236, 237, 240, 241, 242, 244, 245, 247, 249, 251, 252, 253, 256, 258, 259, 260], "branches": [[197, 198], [200, 201], [200, 202], [212, 213], [215, 216], [215, 217], [224, 226], [224, 249], [231, 232], [231, 240], [233, 231], [233, 234], [235, 236], [235, 237], [241, 242], [241, 247], [242, 244], [251, 252], [251, 256]]}

import importlib
import pandas as pd
import pytest

# Import the module under test
submit_mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.select.submit")
BestValidSelector = submit_mod.BestValidSelector

# Helper lightweight classes used in tests
class FakeExperiment:
    def __init__(self, result):
        self.result = result

class FakeFeedback:
    def __init__(self, decision: bool):
        self.decision = decision

class FakeScen:
    def __init__(self, metric_direction: bool):
        self.metric_direction = metric_direction

class FakeTrace:
    def __init__(self, scen, hist=None, ev_list=None, parents_map=None):
        # hist: list of tuples (exp, feedback)
        self.scen = scen
        self.hist = hist or []
        self._ev_list = ev_list or []
        # parents_map: mapping node index -> list of parents
        self._parents_map = parents_map or {}

    def get_parents(self, node_idx):
        return self._parents_map.get(node_idx, [])

    def experiment_and_feedback_list_after_init(self, return_type="all", search_type="all"):
        # ignore args, return prepared list
        return list(self._ev_list)


def make_df_with_ensemble(value):
    # Create a DataFrame with index 'ensemble' so .loc['ensemble'].iloc[0] works
    return pd.DataFrame([value], index=["ensemble"])


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)


def test_collect_candidates_each_trace_false_string_and_numeric_scores():
    # Set up two experiments: one with a numeric score, one with a string wrapped score.
    exp_num = FakeExperiment(make_df_with_ensemble(0.5))
    fb_num = FakeFeedback(decision=True)

    exp_str = FakeExperiment(make_df_with_ensemble("tensor(0.9)"))
    fb_str = FakeFeedback(decision=False)

    # Trace with metric_direction True (direction_sign = 1)
    scen = FakeScen(metric_direction=True)
    trace = FakeTrace(scen, ev_list=[(exp_num, fb_num), (exp_str, fb_str)])

    selector = BestValidSelector(num_candidates=1, use_decision=True, each_trace=False)
    top = selector.collect_sota_candidates(trace)

    assert isinstance(top, list)
    assert len(top) == 1
    # The string "tensor(0.9)" should be parsed to 0.9 and be the selected top experiment
    assert top[0] is exp_str


def test_collect_candidates_each_trace_true_with_exception_and_decision(monkeypatch):
    # Patch the module logger with a dummy so we can capture loguru-based warnings
    dummy = DummyLogger()
    monkeypatch.setattr(submit_mod, "logger", dummy)

    # Create experiments:
    e0 = FakeExperiment(make_df_with_ensemble(0.1))
    f0 = FakeFeedback(decision=True)
    e1 = FakeExperiment(make_df_with_ensemble(0.3))
    f1 = FakeFeedback(decision=False)
    e2 = FakeExperiment(make_df_with_ensemble("tensor(0.8)"))
    f2 = FakeFeedback(decision=True)
    # This result will cause DataFrame.loc['ensemble'] to KeyError -> should trigger warning
    e3 = FakeExperiment({"not_ensemble": [42]})
    f3 = FakeFeedback(decision=True)

    hist = [(e0, f0), (e1, f1), (e2, f2), (e3, f3)]
    parents_map = {0: [], 1: [0], 2: [0], 3: [1]}
    scen = FakeScen(metric_direction=True)
    trace = FakeTrace(scen, hist=hist, parents_map=parents_map)

    selector = BestValidSelector(num_candidates=3, use_decision=True, each_trace=True)
    top = selector.collect_sota_candidates(trace)

    # Ensure a warning was logged for the failing score extraction (e3)
    assert any("Failed to extract score from result" in str(m) for m in dummy.warnings)

    assert isinstance(top, list)
    assert len(top) == 3
    # The best experiment by score should be e2 (0.8)
    assert top[0] is e2
    # e1 should be present among the selected
    assert any(item is e1 for item in top)
    # e3 should be present as it originates from a branch and is included even if its extraction failed
    assert any(item is e3 for item in top)


def test_collect_candidates_empty_returns_none(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(submit_mod, "logger", dummy)

    scen = FakeScen(metric_direction=True)
    trace = FakeTrace(scen, ev_list=[])

    selector = BestValidSelector(num_candidates=2, use_decision=True, each_trace=False)
    res = selector.collect_sota_candidates(trace)

    assert res is None
    assert any("BestValidSelector: No experiments found in trace." in str(m) for m in dummy.infos)
