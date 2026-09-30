import pandas as pd
from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator

class NonDatetimeNoSub:
    """Custom objects that will raise TypeError on subtraction to simulate non-datetime index values."""
    def __repr__(self):
        return "NonDatetimeNoSub()"

    def __sub__(self, other):
        raise TypeError("unsupported operand type(s) for -: 'NonDatetimeNoSub' and '{}'".format(type(other).__name__))


def test_probe_001_non_datetime_index_level_returns_false_and_not_raise():
    # Build a deterministic MultiIndex where level name 'datetime' exists but contains non-datetime objects
    dt_level = [NonDatetimeNoSub(), NonDatetimeNoSub(), NonDatetimeNoSub()]
    id_level = [1, 2, 3]
    idx = pd.MultiIndex.from_arrays([dt_level, id_level], names=["datetime", "id"])

    gen_df = pd.DataFrame({"val": [10, 20, 30]}, index=idx)

    # Instantiate without calling __init__ to avoid unknown side-effects
    evaluator = FactorDatetimeDailyEvaluator.__new__(FactorDatetimeDailyEvaluator)

    # Monkeypatch the instance _get_df to return our crafted dataframe deterministically.
    # Fix: ensure the bound method accepts self as the first parameter so binding does not cause an argument-count error.
    def _get_df(self, gt_impl, impl):
        return (None, gen_df)

    # bind the function as a method on the evaluator instance
    evaluator._get_df = _get_df.__get__(evaluator, FactorDatetimeDailyEvaluator)

    # Call evaluate and assert the independent oracle: no exception and returns (message, False)
    result = evaluator.evaluate(None, None)

    assert isinstance(result, tuple), "evaluate must return a tuple"
    assert result[1] is False, "When 'datetime' index level contains non-datetime values, the evaluator should indicate non-daily (False)"
