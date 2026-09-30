import importlib
from types import SimpleNamespace
import pytest

submit = importlib.import_module(
    "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"
)
ValidationSelector = submit.ValidationSelector


def make_instance():
    # Create an instance without invoking __init__ so we can set attributes deterministically
    inst = object.__new__(ValidationSelector)
    # Provide minimal attributes used by get_sota_exp_to_submit
    inst.competition = "mock_comp"
    inst.candidate = []
    inst.hypothesis_exp = {}
    inst.hypothesis_loop_id = {}
    inst.direction_sign = 1
    return inst


def test_prepare_scripts_runtime_error_round_100(monkeypatch):
    inst = make_instance()
    # candidate must have at least one element because code accesses candidate[0][0]
    fake_exp = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h0"))
    inst.candidate = [(fake_exp, 1)]

    # Patch the instance method to raise RuntimeError to exercise the except branch
    def bad_prepare(reference_exp, competition, mock_folder):
        raise RuntimeError("prep failed")

    inst._prepare_validation_scripts = bad_prepare

    # Patch shutil.rmtree to observe it is called (no real FS operations)
    called = {"rmtree": False, "args": None}

    def fake_rmtree(path, ignore_errors=False):
        called["rmtree"] = True
        called["args"] = (path, ignore_errors)

    monkeypatch.setattr(submit, "shutil", submit.shutil)
    monkeypatch.setattr(submit.shutil, "rmtree", fake_rmtree)

    res = inst.get_sota_exp_to_submit(trace=None)

    assert res is None
    # Confirm that cleanup was attempted on the mock folder
    assert called["rmtree"] is True
    assert "/tmp/mock/" in called["args"][0]


def test_no_results_round_100(monkeypatch):
    inst = make_instance()
    fake_exp = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h0"))
    inst.candidate = [(fake_exp, 1)]

    # Normal prepare returning dummy scripts
    def ok_prepare(reference_exp, competition, mock_folder):
        return "data_code", "grade_code"

    inst._prepare_validation_scripts = ok_prepare

    # Patch multiprocessing_wrapper to return empty results to exercise the "no results" branch
    monkeypatch.setattr(submit, "multiprocessing_wrapper", lambda tasks, n: [])

    # Avoid real rmtree
    monkeypatch.setattr(submit.shutil, "rmtree", lambda *a, **k: None)

    res = inst.get_sota_exp_to_submit(trace=None)
    assert res is None


def test_all_test_scores_none_round_100(monkeypatch):
    inst = make_instance()
    # Create an experiment whose hypothesis key will be used
    exp_obj = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h_none"))
    inst.candidate = [(exp_obj, 1)]

    inst._prepare_validation_scripts = lambda reference_exp, competition, mock_folder: ("d", "g")

    # multiprocessing returns one result with test_score == None -> filtered out
    monkeypatch.setattr(submit, "multiprocessing_wrapper", lambda tasks, n: [(exp_obj, 0.5, None)])
    monkeypatch.setattr(submit.shutil, "rmtree", lambda *a, **k: None)

    res = inst.get_sota_exp_to_submit(trace=None)
    assert res is None


def test_equal_test_scores_warn_round_100(monkeypatch):
    inst = make_instance()

    # Two experiments with different hypothesis ids
    exp1 = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h1"))
    exp2 = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="h2"))

    inst.candidate = [(exp1, 10), (exp2, 20)]

    inst._prepare_validation_scripts = lambda reference_exp, competition, mock_folder: ("d", "g")

    # Provide mappings from hypothesis key -> returned experiment object and loop id
    inst.hypothesis_exp = {"h1": "E1", "h2": "E2"}
    inst.hypothesis_loop_id = {"h1": 10, "h2": 20}

    # Both results have equal test_score -> triggers the branch where top == last -> returns None
    monkeypatch.setattr(
        submit,
        "multiprocessing_wrapper",
        lambda tasks, n: [(exp1, 0.7, 0.9), (exp2, 0.8, 0.9)],
    )
    monkeypatch.setattr(submit.shutil, "rmtree", lambda *a, **k: None)

    res = inst.get_sota_exp_to_submit(trace=None)
    assert res is None


def test_successful_selection_round_100(monkeypatch):
    inst = make_instance()

    exp_a = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="ha"))
    exp_b = SimpleNamespace(hypothesis=SimpleNamespace(hypothesis="hb"))

    inst.candidate = [(exp_a, 1), (exp_b, 2)]

    inst._prepare_validation_scripts = lambda reference_exp, competition, mock_folder: ("d", "g")

    # Map hypothesis keys to final experiment objects and loop ids the selector should return
    inst.hypothesis_exp = {"ha": "FINAL_A", "hb": "FINAL_B"}
    inst.hypothesis_loop_id = {"ha": 1, "hb": 2}

    # Two results with different test scores; higher test score should be selected
    monkeypatch.setattr(
        submit,
        "multiprocessing_wrapper",
        lambda tasks, n: [(exp_a, 0.6, 0.4), (exp_b, 0.7, 0.9)],
    )
    monkeypatch.setattr(submit.shutil, "rmtree", lambda *a, **k: None)

    res = inst.get_sota_exp_to_submit(trace=None)
    # The selector returns the mapped hypothesis_exp value for the best test score
    assert res == "FINAL_B"
