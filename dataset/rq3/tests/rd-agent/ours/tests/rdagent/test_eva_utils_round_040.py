import importlib
import pandas as pd

import rdagent.components.coder.factor_coder.eva_utils as eva_utils


class _StubEval:
    def __init__(self, ret):
        # ret should be a tuple returned by evaluate
        self._ret = ret

    def evaluate(self, implementation, gt_implementation):
        return self._ret


class _StubEvalNoGt:
    def __init__(self, ret):
        self._ret = ret

    def evaluate(self, implementation, gt_implementation):
        # allow being called and ignore inputs
        return self._ret


def _make_scen(input_shape=None):
    class S:
        pass

    s = S()
    s.input_shape = input_shape
    return s


def test_value_evaluator_version1_equal_high_row_mismatch_round_040():
    # Arrange: patch evaluator classes in module to deterministic stubs
    mod = eva_utils

    # Keep originals to restore later
    orig = {
        'FactorSingleColumnEvaluator': mod.FactorSingleColumnEvaluator,
        'FactorInfEvaluator': mod.FactorInfEvaluator,
        'FactorOutputFormatEvaluator': mod.FactorOutputFormatEvaluator,
        'FactorDatetimeDailyEvaluator': mod.FactorDatetimeDailyEvaluator,
        'FactorRowCountEvaluator': mod.FactorRowCountEvaluator,
        'FactorIndexEvaluator': mod.FactorIndexEvaluator,
        'FactorMissingValuesEvaluator': mod.FactorMissingValuesEvaluator,
        'FactorEqualValueRatioEvaluator': mod.FactorEqualValueRatioEvaluator,
        'FactorCorrelationEvaluator': mod.FactorCorrelationEvaluator,
    }

    try:
        # Version==1 should call SingleColumnEvaluator
        mod.FactorSingleColumnEvaluator = lambda scen: _StubEval(("single_col_ok", None))
        # Inf evaluator returns feedback and True
        mod.FactorInfEvaluator = lambda scen: _StubEval(("inf_ok", True))
        # Output format evaluator returns feedback and True
        mod.FactorOutputFormatEvaluator = lambda scen: _StubEval(("out_ok", True))
        # Datetime daily evaluator (version 1) returns feedback and True
        mod.FactorDatetimeDailyEvaluator = lambda scen: _StubEval(("daily_ok", True))

        # Row count evaluator returns feedback and a value greater than None (but not fail)
        mod.FactorRowCountEvaluator = lambda scen: _StubEval(("row_ok", 1.0))
        # Index evaluator returns feedback and index_result less than threshold to force else branch
        mod.FactorIndexEvaluator = lambda scen: _StubEval(("idx_ok", 0.5))
        mod.FactorMissingValuesEvaluator = lambda scen: _StubEval(("miss_ok", True))
        # Equal value ratio returns >0.99 to trigger decision True
        mod.FactorEqualValueRatioEvaluator = lambda scen: _StubEval(("eq_ok", 1.0))
        # Correlation evaluator shouldn't be called in this test because index_result < 0.99
        mod.FactorCorrelationEvaluator = lambda **kw: _StubEval(("corr_called", False))

        # Create scen and evaluator
        scen = _make_scen(input_shape=(None, 3))
        evaluator = mod.FactorValueEvaluator(scen)

        # Use simple placeholders for implementation and gt_implementation
        impl = object()
        gt_impl = object()

        # Act
        conclusion, decision = evaluator.evaluate(impl, gt_impl, version=1)

        # Assert
        assert isinstance(conclusion, str)
        # single column feedback should be present first
        assert "single_col_ok" in conclusion
        # equality evaluator feedback should be included
        assert "eq_ok" in conclusion
        # Because equal_value_ratio_result == 1.0 (>0.99), final decision should be True
        assert decision is True

    finally:
        # restore
        for k, v in orig.items():
            setattr(mod, k, v)


def test_value_evaluator_version2_more_columns_and_row_failure_round_040():
    mod = eva_utils

    orig = {
        'FactorInfEvaluator': mod.FactorInfEvaluator,
        'FactorOutputFormatEvaluator': mod.FactorOutputFormatEvaluator,
        'FactorDatetimeDailyEvaluator': mod.FactorDatetimeDailyEvaluator,
        'FactorRowCountEvaluator': mod.FactorRowCountEvaluator,
        'FactorIndexEvaluator': mod.FactorIndexEvaluator,
        'FactorMissingValuesEvaluator': mod.FactorMissingValuesEvaluator,
        'FactorEqualValueRatioEvaluator': mod.FactorEqualValueRatioEvaluator,
        'FactorCorrelationEvaluator': mod.FactorCorrelationEvaluator,
    }

    try:
        # For version 2: no SingleColumnEvaluator call. We must patch _get_df to produce gen_df with more columns
        # Patch evaluators
        mod.FactorInfEvaluator = lambda scen: _StubEval(("inf_ok", True))
        mod.FactorOutputFormatEvaluator = lambda scen: _StubEval(("out_ok", True))
        # DatetimeDailyEvaluator is not used for version 2 so can be left but patch to safe value
        mod.FactorDatetimeDailyEvaluator = lambda scen: _StubEval(("daily_ok", True))

        # RowCount returns a small ratio triggering decision False (<=0.99)
        mod.FactorRowCountEvaluator = lambda scen: _StubEval(("row_low", 0.5))
        # Index returns >0.99 so FactorCorrelationEvaluator will be invoked
        mod.FactorIndexEvaluator = lambda scen: _StubEval(("idx_high", 1.0))
        mod.FactorMissingValuesEvaluator = lambda scen: _StubEval(("miss_ok", True))
        mod.FactorEqualValueRatioEvaluator = lambda scen: _StubEval(("eq_low", 0.0))

        # Correlation evaluator invoked when index_result > 0.99
        def corr_factory(**kwargs):
            # return a callable class instance that has evaluate
            return _StubEval(("corr_result", False))

        mod.FactorCorrelationEvaluator = corr_factory

        # Patch _get_df on FactorValueEvaluator to return a gen_df with 2 columns while scen.input_shape has 1
        def _fake_get_df(self, gt_impl, impl):
            # create a DataFrame with 2 columns to simulate extra generated columns
            df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
            return None, df

        orig_get_df = mod.FactorValueEvaluator._get_df
        mod.FactorValueEvaluator._get_df = _fake_get_df

        scen = _make_scen(input_shape=(None, 1))
        evaluator = mod.FactorValueEvaluator(scen)

        impl = object()
        gt_impl = object()

        conclusion, decision = evaluator.evaluate(impl, gt_impl, version=2)

        # The conclusion should include the warning about too many columns
        assert "Output dataframe has more columns" in conclusion
        # Because row_result was 0.5 (<=0.99), decision should be False
        assert decision is False

    finally:
        for k, v in orig.items():
            setattr(mod, k, v)
        mod.FactorValueEvaluator._get_df = orig_get_df


def test_value_evaluator_version2_gt_none_returns_none_decision_round_040():
    mod = eva_utils

    orig = {
        'FactorInfEvaluator': mod.FactorInfEvaluator,
        'FactorOutputFormatEvaluator': mod.FactorOutputFormatEvaluator,
        'FactorRowCountEvaluator': mod.FactorRowCountEvaluator,
        'FactorIndexEvaluator': mod.FactorIndexEvaluator,
        'FactorMissingValuesEvaluator': mod.FactorMissingValuesEvaluator,
        'FactorEqualValueRatioEvaluator': mod.FactorEqualValueRatioEvaluator,
        'FactorCorrelationEvaluator': mod.FactorCorrelationEvaluator,
    }

    try:
        # Patch evaluators such that no failing flags and no high equality or correlation
        mod.FactorInfEvaluator = lambda scen: _StubEval(("inf_ok", True))
        mod.FactorOutputFormatEvaluator = lambda scen: _StubEval(("out_ok", True))
        mod.FactorRowCountEvaluator = lambda scen: _StubEval(("row_ok", None))
        mod.FactorIndexEvaluator = lambda scen: _StubEval(("idx_ok", 0.0))
        mod.FactorMissingValuesEvaluator = lambda scen: _StubEval(("miss_ok", True))
        mod.FactorEqualValueRatioEvaluator = lambda scen: _StubEval(("eq_low", 0.0))

        mod.FactorCorrelationEvaluator = lambda **kw: _StubEval(("corr_n/a", False))

        # Ensure _get_df returns something valid but not exceeding columns
        def _fake_get_df2(self, gt_impl, impl):
            df = pd.DataFrame({"a": [1, 2]})
            return None, df

        orig_get_df = mod.FactorValueEvaluator._get_df
        mod.FactorValueEvaluator._get_df = _fake_get_df2

        scen = _make_scen(input_shape=(None, 1))
        evaluator = mod.FactorValueEvaluator(scen)

        impl = object()
        # gt_implementation is None to skip the block that populates row_result etc.
        conclusion, decision = evaluator.evaluate(impl, None, version=2)

        # Because gt is None and no failing condition happened (inf True, equality low, correlation False), decision should be None
        assert decision is None
        assert isinstance(conclusion, str)

    finally:
        for k, v in orig.items():
            setattr(mod, k, v)
        mod.FactorValueEvaluator._get_df = orig_get_df
