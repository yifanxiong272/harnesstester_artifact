# file: rdagent/log/ui/app.py:142-255
# asked: {"lines": [142, 143, 144, 145, 146, 147, 148, 149, 150, 153, 154, 155, 158, 159, 160, 161, 163, 165, 166, 168, 169, 172, 174, 175, 176, 178, 179, 180, 181, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 194, 201, 202, 203, 204, 205, 208, 209, 210, 211, 212, 214, 221, 222, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 245, 246, 248, 251, 252, 253, 254, 255], "branches": [[143, 0], [143, 144], [144, 145], [147, 144], [147, 148], [149, 150], [149, 153], [165, 166], [165, 168], [172, 174], [172, 228], [174, 178], [174, 186], [186, 187], [186, 208], [191, 192], [191, 208], [192, 201], [192, 203], [212, 221], [212, 224], [228, 229], [228, 230], [230, 231], [230, 232], [232, 233], [232, 245], [236, 237], [236, 239], [237, 236], [237, 238], [245, 246], [245, 248], [251, 144], [251, 252]]}
# gained: {"lines": [142, 143, 144, 145, 146, 147, 148, 149, 150, 153, 154, 155, 158, 159, 160, 161, 163, 165, 166, 168, 169, 172, 174, 175, 176, 178, 179, 182, 183, 184, 186, 187, 188, 191, 192, 194, 201, 202, 203, 204, 205, 208, 209, 212, 214, 221, 222, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 245, 246, 248, 251, 252, 253, 254, 255], "branches": [[143, 144], [144, 145], [147, 148], [149, 150], [149, 153], [165, 166], [165, 168], [172, 174], [172, 228], [174, 178], [186, 187], [191, 192], [192, 201], [212, 221], [228, 229], [228, 230], [230, 231], [230, 232], [232, 233], [232, 245], [236, 237], [236, 239], [237, 236], [237, 238], [245, 246], [251, 144], [251, 252]]}

import importlib
import sys
import types
import collections
import pandas as pd
import pytest


def import_app_with_clean_argv(monkeypatch):
    # ensure argparse in module import doesn't pick up pytest args
    monkeypatch.setattr(sys, "argv", ["testprog"])
    # force re-import to apply argv change
    mod_name = "rdagent.log.ui.app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


class DummyScenario:
    pass


class DummyHF:
    def __init__(self, decision):
        self.decision = decision


class DummyExp:
    def __init__(self, result):
        self.result = result


class DummyContent:
    def __init__(self, based_experiments, result):
        self.based_experiments = based_experiments
        self.result = result


class DummyMsg:
    def __init__(self, tag, content):
        self.tag = tag
        self.content = content


def make_state():
    S = types.SimpleNamespace()
    S.fs = None
    S.current_tags = []
    S.lround = 0
    S.erounds = collections.defaultdict(int)
    S.last_msg = None
    S.scenario = None
    S.alpha_baseline_metrics = None
    S.metric_series = []
    S.all_metric_series = []
    S.h_decisions = {}
    S.hypotheses = {}
    S.e_decisions = collections.defaultdict(dict)
    S.msgs = collections.defaultdict(lambda: collections.defaultdict(list))
    return S


def setup_common_monkeypatches(app, monkeypatch):
    # make should_display always True
    monkeypatch.setattr(app, "should_display", lambda m: True, raising=False)
    # set selectable metrics
    monkeypatch.setattr(app, "QLIB_SELECTED_METRICS", ["m1", "m2"], raising=False)
    # monkeypatch scenario classes so isinstance checks work
    monkeypatch.setattr(app, "QlibFactorScenario", DummyScenario, raising=False)
    monkeypatch.setattr(app, "QlibQuantScenario", DummyScenario, raising=False)
    monkeypatch.setattr(app, "QlibModelScenario", DummyScenario, raising=False)
    monkeypatch.setattr(app, "QlibFactorFromReportScenario", DummyScenario, raising=False)
    monkeypatch.setattr(app, "HypothesisFeedback", DummyHF, raising=False)


def test_runner_result_and_metric_series(monkeypatch):
    app = import_app_with_clean_argv(monkeypatch)
    setup_common_monkeypatches(app, monkeypatch)

    state = make_state()
    state.scenario = DummyScenario()
    state.lround = 1
    state.alpha_baseline_metrics = None

    full_series = pd.Series([0.1, 0.2, 0.3], index=["m1", "m2", "other"])
    be0 = DummyExp(full_series)
    be_last = DummyExp(full_series)
    content = DummyContent(based_experiments=[be0, be_last], result=full_series)
    msg = DummyMsg("runner result", content)

    state.fs = iter([msg])

    # replace streamlit toast to avoid UI effects
    monkeypatch.setattr(app, "st", types.SimpleNamespace(toast=lambda *a, **k: None), raising=False)
    # inject our state
    monkeypatch.setattr(app, "state", state, raising=False)

    # run
    app.get_msgs_until(end_func=lambda m: True)

    # assertions
    assert state.alpha_baseline_metrics is not None
    assert list(state.alpha_baseline_metrics.index) == ["m1", "m2"]
    assert len(state.metric_series) >= 2
    assert state.metric_series[-1].name == "Round 1"
    assert len(state.all_metric_series) >= 2
    assert state.all_metric_series[-1].name == "Round 1"
    assert state.last_msg is msg
    assert "runner result" in state.msgs[state.lround]


def test_various_tags_and_stopiteration(monkeypatch):
    app = import_app_with_clean_argv(monkeypatch)
    setup_common_monkeypatches(app, monkeypatch)

    state = make_state()
    state.current_tags = []
    state.lround = 0
    state.erounds[0] = 0

    hyp_msg = DummyMsg("hypothesis generation.init", {"some": "hyp"})
    ev_code_msg = DummyMsg("evolving code", [None, "", "keep", 0, "also"])

    class WSF:
        def __init__(self, final_decision):
            self.final_decision = final_decision

    ev_feedback_msg = DummyMsg("something.evolving feedback", [WSF(True), WSF(False), WSF(True)])
    hf = DummyHF(decision="approved")
    feedback_msg = DummyMsg("feedback", hf)

    state.fs = iter([hyp_msg, ev_code_msg, ev_feedback_msg, feedback_msg])

    called = {"toast": 0}

    def fake_toast(*a, **k):
        called["toast"] += 1

    monkeypatch.setattr(app, "st", types.SimpleNamespace(toast=fake_toast), raising=False)
    monkeypatch.setattr(app, "state", state, raising=False)

    app.get_msgs_until(end_func=lambda m: False)

    assert state.lround >= 1
    assert state.hypotheses.get(state.lround) == {"some": "hyp"}

    # find evolving code messages stored
    found_ev_msgs = []
    for msgs in state.msgs[state.lround].values():
        for m in msgs:
            if "evolving code" in m.tag:
                found_ev_msgs.append(m)
    assert len(found_ev_msgs) >= 1
    assert found_ev_msgs[-1].content == ["keep", "also"]

    idx = state.erounds[state.lround]
    assert idx in state.e_decisions[state.lround]
    right_num, wrong_num, none_num = state.e_decisions[state.lround][idx]
    assert right_num == 2
    assert wrong_num == 1
    assert none_num == 0

    assert state.h_decisions[state.lround] == "approved"
    assert called["toast"] == 1
    assert len(state.msgs[state.lround]) > 0
