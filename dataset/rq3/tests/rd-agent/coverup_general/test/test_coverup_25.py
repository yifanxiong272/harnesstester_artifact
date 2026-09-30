# file: rdagent/components/coder/factor_coder/eva_utils.py:390-475
# asked: {"lines": [397, 400, 401, 402, 403, 404, 405, 408, 409, 410, 411, 412, 413, 414, 415, 416, 419, 420, 423, 424, 425, 426, 427, 429, 431, 434, 435, 436, 438, 439, 441, 442, 444, 446, 447, 449, 451, 452, 453, 454, 456, 457, 458, 461, 463, 464, 466, 467, 468, 469, 470, 472, 474, 475], "branches": [[408, 409], [408, 411], [411, 412], [411, 419], [414, 415], [414, 419], [425, 426], [425, 431], [434, 435], [434, 461], [451, 452], [451, 456], [463, 464], [463, 465], [465, 472], [465, 474]]}
# gained: {"lines": [397, 400, 401, 402, 403, 404, 405, 408, 409, 410, 411, 412, 413, 414, 415, 416, 419, 420, 423, 424, 425, 426, 427, 429, 431, 434, 435, 436, 438, 439, 441, 442, 444, 446, 447, 449, 451, 452, 453, 454, 456, 457, 458, 461, 463, 464, 466, 467, 468, 469, 470, 472, 474, 475], "branches": [[408, 409], [408, 411], [411, 412], [414, 415], [425, 426], [425, 431], [434, 435], [434, 461], [451, 452], [451, 456], [463, 464], [463, 465], [465, 472], [465, 474]]}

import pandas as pd
import pytest
from types import SimpleNamespace

import rdagent.components.coder.factor_coder.eva_utils as eva_utils
from rdagent.components.coder.factor_coder.eva_utils import FactorValueEvaluator


def _fake_evaluator_factory(return_value):
    class FakeEvaluator:
        def __init__(self, *args, **kwargs):
            pass

        def evaluate(self, implementation, gt_implementation):
            return return_value

    return FakeEvaluator


def _fake_evaluator_factory_fn(fn):
    class FakeEvaluator:
        def __init__(self, *args, **kwargs):
            pass

        def evaluate(self, implementation, gt_implementation):
            return fn(implementation, gt_implementation)

    return FakeEvaluator


def _make_instance():
    # Create instance without calling original __init__, to avoid unknown constructor signature
    inst = object.__new__(FactorValueEvaluator)
    inst.scen = SimpleNamespace(input_shape=(None, 3))
    return inst


def test_evaluate_version1_equal_value_triggers_true(monkeypatch):
    # Setup fake evaluators to hit branch where equal_value_ratio_result > 0.99 => decision True
    monkeypatch.setattr(
        eva_utils,
        "FactorSingleColumnEvaluator",
        _fake_evaluator_factory(("singlecol_feedback", None)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorInfEvaluator",
        _fake_evaluator_factory(("inf_feedback", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorOutputFormatEvaluator",
        _fake_evaluator_factory(("output_format_feedback", None)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorDatetimeDailyEvaluator",
        _fake_evaluator_factory(("daily_feedback", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorRowCountEvaluator",
        _fake_evaluator_factory(("row_feedback", 10)),  # >0.99
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorIndexEvaluator",
        _fake_evaluator_factory(("index_feedback", 0.5)),  # <0.99 so no corr evaluator
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorMissingValuesEvaluator",
        _fake_evaluator_factory(("missing_feedback", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorEqualValueRatioEvaluator",
        _fake_evaluator_factory(("equal_feedback", 0.995)),  # >0.99 triggers True
    )
    # Correlation evaluator shouldn't be called in this scenario, but provide a harmless fake
    monkeypatch.setattr(
        eva_utils,
        "FactorCorrelationEvaluator",
        _fake_evaluator_factory(("corr_feedback", False)),
    )

    evaluator = _make_instance()
    # Provide dummy implementation and gt_implementation (not None)
    impl = object()
    gt_impl = object()

    conclusion_str, decision = evaluator.evaluate(impl, gt_impl, version=1)

    # Assertions: decision should be True because equal_value_ratio_result > 0.99
    assert decision is True
    # Ensure feedback strings from the evaluators appear in the combined conclusion
    assert "singlecol_feedback" in conclusion_str
    assert "inf_feedback" in conclusion_str
    assert "output_format_feedback" in conclusion_str
    assert "daily_feedback" in conclusion_str
    assert "row_feedback" in conclusion_str
    assert "index_feedback" in conclusion_str
    assert "missing_feedback" in conclusion_str
    assert "equal_feedback" in conclusion_str


def test_evaluate_version1_row_count_triggers_false_and_correlation_called(monkeypatch):
    # Setup fake evaluators to hit branch where row_result <= 0.99 => decision False
    monkeypatch.setattr(
        eva_utils,
        "FactorSingleColumnEvaluator",
        _fake_evaluator_factory(("singlecol_feedback2", None)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorInfEvaluator",
        _fake_evaluator_factory(("inf_feedback2", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorOutputFormatEvaluator",
        _fake_evaluator_factory(("output_format_feedback2", None)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorDatetimeDailyEvaluator",
        _fake_evaluator_factory(("daily_feedback2", True)),
    )
    # row_result small to force False outcome
    monkeypatch.setattr(
        eva_utils,
        "FactorRowCountEvaluator",
        _fake_evaluator_factory(("row_feedback2", 0.5)),
    )
    # index_result > 0.99 so FactorCorrelationEvaluator should be invoked
    monkeypatch.setattr(
        eva_utils,
        "FactorIndexEvaluator",
        _fake_evaluator_factory(("index_feedback2", 1.0)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorMissingValuesEvaluator",
        _fake_evaluator_factory(("missing_feedback2", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorEqualValueRatioEvaluator",
        _fake_evaluator_factory(("equal_feedback2", 0.0)),
    )

    # Make correlation evaluator return (feedback, False) to exercise that branch too
    monkeypatch.setattr(
        eva_utils,
        "FactorCorrelationEvaluator",
        _fake_evaluator_factory(("corr_feedback2", False)),
    )

    evaluator = _make_instance()
    impl = object()
    gt_impl = object()

    conclusion_str, decision = evaluator.evaluate(impl, gt_impl, version=1)

    # decision should be False because row_result <= 0.99
    assert decision is False
    # Ensure correlation feedback was appended (since index_result > 0.99)
    assert "corr_feedback2" in conclusion_str
    # Ensure other feedbacks included
    assert "singlecol_feedback2" in conclusion_str
    assert "row_feedback2" in conclusion_str
    assert "index_feedback2" in conclusion_str
    assert "equal_feedback2" in conclusion_str


def test_evaluate_version2_no_gt_implementation_results_in_none_decision_and_column_count_message(monkeypatch):
    # Version 2 path: ensure when gen_df has more columns than scen.input_shape triggers the message
    # Monkeypatch evaluators used regardless (some won't be called because gt_impl is None)
    monkeypatch.setattr(
        eva_utils,
        "FactorSingleColumnEvaluator",
        _fake_evaluator_factory(("should_not_be_called", None)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorInfEvaluator",
        _fake_evaluator_factory(("inf_feedback_v2", True)),
    )
    monkeypatch.setattr(
        eva_utils,
        "FactorOutputFormatEvaluator",
        _fake_evaluator_factory(("output_format_feedback_v2", None)),
    )
    # For version==2 daily_check_result is set to None by code path; still provide a fake in case not used
    monkeypatch.setattr(
        eva_utils,
        "FactorDatetimeDailyEvaluator",
        _fake_evaluator_factory(("daily_feedback_v2", None)),
    )
    # Ensure row/index/missing/equal/corr exist but shouldn't be called because gt_impl is None
    monkeypatch.setattr(eva_utils, "FactorRowCountEvaluator", _fake_evaluator_factory(("r", 1)))
    monkeypatch.setattr(eva_utils, "FactorIndexEvaluator", _fake_evaluator_factory(("i", 1)))
    monkeypatch.setattr(eva_utils, "FactorMissingValuesEvaluator", _fake_evaluator_factory(("m", True)))
    monkeypatch.setattr(eva_utils, "FactorEqualValueRatioEvaluator", _fake_evaluator_factory(("e", 0.0)))
    monkeypatch.setattr(eva_utils, "FactorCorrelationEvaluator", _fake_evaluator_factory(("c", False)))

    # Create evaluator instance and patch its scen input_shape to have fewer columns (e.g., 3)
    evaluator = _make_instance()
    evaluator.scen = SimpleNamespace(input_shape=(None, 3))

    # Patch _get_df to return gen_df with more columns than input_shape[-1] to hit message
    gen_df = pd.DataFrame([[1, 2, 3, 4, 5]])
    def _get_df(gt_impl, impl):
        return None, gen_df

    evaluator._get_df = _get_df

    impl = object()
    gt_impl = None  # key: gt_implementation is None to skip many checks and get None decision

    conclusion_str, decision = evaluator.evaluate(impl, gt_impl, version=2)

    # decision should be None because gt_impl is None and no other failing condition is present
    assert decision is None
    # Check that the specific "more columns than input feature" message was appended
    assert "Output dataframe has more columns than input feature which is not acceptable in feature processing tasks" in conclusion_str
    # Check that inf evaluator feedback is present
    assert "inf_feedback_v2" in conclusion_str
