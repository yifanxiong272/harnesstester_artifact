import pandas as pd
from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator


def test_probe_001_detects_non_daily_with_2h_gap():
    # Deterministic datetime sequence with one sub-daily 2-hour gap among otherwise daily spacing
    dates = [
        pd.Timestamp("2022-01-01 00:00"),
        pd.Timestamp("2022-01-02 00:00"),
        pd.Timestamp("2022-01-02 02:00"),  # 2-hour gap relative to previous
        pd.Timestamp("2022-01-03 00:00"),
    ]

    # Create a MultiIndex with a single level named 'datetime' per activation conditions
    mi = pd.MultiIndex.from_arrays([dates], names=["datetime"])
    gen_df = pd.DataFrame({"val": [1, 2, 3, 4]}, index=mi)

    # Instantiate without running potential complex __init__ and monkeypatch _get_df
    evaluator = object.__new__(FactorDatetimeDailyEvaluator)
    # _get_df is expected to be called as _get_df(gt_implementation, implementation)
    evaluator._get_df = lambda gt_implementation, implementation: (None, gen_df)

    implementation = object()
    gt_implementation = object()

    result = evaluator.evaluate(implementation, gt_implementation)

    # Primary behavioral oracle: evaluator must report non-daily and False when a 2-hour gap exists
    assert result == (
        "The generated dataframe is not daily. The implementation is definitely wrong. Please check the implementation.",
        False,
    )
