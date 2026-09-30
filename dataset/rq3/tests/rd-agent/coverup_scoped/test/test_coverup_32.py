# file: rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py:289-343
# asked: {"lines": [291, 295, 297, 298, 299, 301, 302, 303, 304, 306, 307, 308, 310, 312, 313, 314, 317, 318, 319, 320, 321, 322, 324, 325, 327, 328, 329, 331, 332, 334, 335, 336, 337, 339, 340, 341, 343], "branches": [[312, 313], [312, 317], [327, 328], [327, 331], [334, 335], [334, 336], [339, 340], [339, 343]]}
# gained: {"lines": [291, 295, 297, 298, 299, 301, 302, 303, 304, 306, 307, 308, 310, 312, 313, 314, 317, 318, 319, 320, 321, 322, 324, 325, 327, 328, 329, 331, 332, 334, 335, 336, 337, 339, 340, 341, 343], "branches": [[312, 313], [312, 317], [327, 328], [327, 331], [334, 335], [334, 336], [339, 340], [339, 343]]}

import types
from types import SimpleNamespace
import pytest

import importlib

submit_mod = importlib.import_module(
    "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"
)
ValidationSelector = getattr(submit_mod, "ValidationSelector")


def make_exp(key):
    return SimpleNamespace(hypothesis=SimpleNamespace(hypothesis=key))


def _setup_selector():
    sel = ValidationSelector.__new__(ValidationSelector)
    # minimal attributes used by the method
    sel.competition = "comp"
    sel.candidate = []
    sel.hypothesis_exp = {}
    sel.hypothesis_loop_id = {}
    sel.direction_sign = 1
    return sel


def test_prepare_validation_runtime_error_calls_rmtree_and_returns_none(monkeypatch):
    sel = _setup_selector()
    # candidate must be indexable as [0][0]
    ref_exp = object()
    sel.candidate = [(ref_exp, 0)]
    # make _prepare_validation_scripts raise
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(submit_mod, "shutil", submit_mod.shutil)  # ensure attribute exists
    called = {}
    def fake_rmtree(path, ignore_errors=False):
        called["path"] = path
        called["ignore_errors"] = ignore_errors
    monkeypatch.setattr(submit_mod.shutil, "rmtree", fake_rmtree)
    monkeypatch.setattr(ValidationSelector, "_prepare_validation_scripts", _raise, raising=False)
    res = ValidationSelector.get_sota_exp_to_submit(sel, trace=None)
    assert res is None
    # ensure rmtree was called on the expected mock folder
    assert called["path"].endswith("/tmp/mock/comp")
    assert called["ignore_errors"] is True


def test_no_results_returns_none(monkeypatch):
    sel = _setup_selector()
    e1 = make_exp("h1")
    sel.candidate = [(e1, 1)]
    sel.hypothesis_exp = {"h1": "exp1"}
    sel.hypothesis_loop_id = {"h1": 1}
    # prepare scripts returns ok
    monkeypatch.setattr(ValidationSelector, "_prepare_validation_scripts", lambda self, **kw: ("d", "g"))
    # multiprocessing_wrapper returns empty -> triggers warning and None
    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", lambda tasks, n: [])
    res = ValidationSelector.get_sota_exp_to_submit(sel, trace=None)
    assert res is None


def test_valid_results_empty_when_all_test_scores_none(monkeypatch):
    sel = _setup_selector()
    e1 = make_exp("h1")
    sel.candidate = [(e1, 1)]
    sel.hypothesis_exp = {"h1": "exp1"}
    sel.hypothesis_loop_id = {"h1": 1}
    monkeypatch.setattr(ValidationSelector, "_prepare_validation_scripts", lambda self, **kw: ("d", "g"))
    # multiprocessing_wrapper returns a result with test_score None -> valid_results becomes empty
    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", lambda tasks, n: [(e1, 0.9, None)])
    res = ValidationSelector.get_sota_exp_to_submit(sel, trace=None)
    assert res is None


def test_single_valid_result_logs_and_returns_none(monkeypatch):
    sel = _setup_selector()
    e1 = make_exp("h1")
    sel.candidate = [(e1, 1)]
    sel.hypothesis_exp = {"h1": "exp1"}
    sel.hypothesis_loop_id = {"h1": 1}
    monkeypatch.setattr(ValidationSelector, "_prepare_validation_scripts", lambda self, **kw: ("d", "g"))
    # single valid result with test_score not None -> len(valid_results) == 1 -> should return None
    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", lambda tasks, n: [(e1, 0.8, 0.7)])
    res = ValidationSelector.get_sota_exp_to_submit(sel, trace=None)
    assert res is None


def test_multiple_valid_results_returns_best_exp(monkeypatch):
    sel = _setup_selector()
    e1 = make_exp("h1")
    e2 = make_exp("h2")
    # Candidate list used to build tasks; values don't affect patched multiprocessing_wrapper's output
    sel.candidate = [(e1, 1), (e2, 2)]
    # Map hypotheses to experiment objects returned
    best_obj = object()
    other_obj = object()
    sel.hypothesis_exp = {"h1": other_obj, "h2": best_obj}
    sel.hypothesis_loop_id = {"h1": 1, "h2": 2}
    sel.direction_sign = 1  # maximize test score
    monkeypatch.setattr(ValidationSelector, "_prepare_validation_scripts", lambda self, **kw: ("d", "g"))
    # Return two results with different test scores; e2 has higher test_score so should be selected
    results = [
        (e1, 0.5, 0.6),  # valid_score, test_score
        (e2, 0.7, 0.9),
    ]
    monkeypatch.setattr(submit_mod, "multiprocessing_wrapper", lambda tasks, n: results)
    res = ValidationSelector.get_sota_exp_to_submit(sel, trace=None)
    assert res is best_obj
