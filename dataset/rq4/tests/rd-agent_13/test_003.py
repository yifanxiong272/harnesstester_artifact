import pandas as pd
from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator


def _make_30min_gen_df(n=10, start="2020-01-01T00:00:00"):
    """Create a DataFrame with a single-level MultiIndex named 'datetime' where
    adjacent timestamps are exactly 30 minutes apart.
    """
    dates = pd.date_range(start=start, periods=n, freq="30T")
    # Use a single-level MultiIndex named 'datetime' so .get_level_values('datetime') works
    idx = pd.MultiIndex.from_arrays([dates], names=["datetime"])
    return pd.DataFrame({"val": range(n)}, index=idx)


def test_probe_001():
    # Deterministic input
    gen_df = _make_30min_gen_df(n=8)

    # Construct evaluator without calling unknown __init__ (safe for tests)
    evaluator = object.__new__(FactorDatetimeDailyEvaluator)

    # Override _get_df to deterministically return our generated dataframe
    evaluator._get_df = lambda gt_impl, impl: (None, gen_df)

    # Expected message exactly as present in the target unit's public code path
    expected_msg = (
        "The generated dataframe is not daily. The implementation is definitely wrong. Please check the implementation."
    )

    # Call the public entrypoint (instance method) with dummy implementations
    result = evaluator.evaluate(None, None)

    # Primary observable oracle: the evaluator must reject sub-day (30-minute) spacing
    assert result == (expected_msg, False), (
        "Invariant violated: evaluator should mark uniform 30-minute-spaced index as non-daily."
    )
