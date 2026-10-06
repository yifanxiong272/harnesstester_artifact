import pandas as pd
from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator

def test_probe_001():
    # Deterministic hourly-spaced datetime index named 'datetime'
    idx = pd.date_range("2021-01-01 00:00:00", periods=24, freq="H", name="datetime")
    gen_df = pd.DataFrame({"val": range(len(idx))}, index=idx)

    # Construct an instance without running __init__ to avoid any required ctor args
    ev = object.__new__(FactorDatetimeDailyEvaluator)

    # Monkeypatch _get_df so evaluate receives our prepared gen_df
    ev._get_df = lambda gt_impl, impl: (None, gen_df)

    # Invoke the targeted entrypoint
    result = ev.evaluate(None, None)

    # Observability checks
    assert isinstance(result, tuple), "evaluate should return a tuple (message, bool)"

    # Primary behavioral oracle: hourly-indexed dataframe should be classified as non-daily
    assert result[1] is False, f"Expected non-daily (False) for hourly index, got {result!r}"
