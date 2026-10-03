import pandas as pd
from rdagent.components.coder.factor_coder.CoSTEER import evaluators


def _make_hourly_df(n=6):
    """Return a DataFrame indexed by a DatetimeIndex named 'datetime' with 1-hour spacing.
    Deterministic construction used to exercise the boundary condition: uniform hourly intervals.
    """
    idx = pd.date_range(start="2020-01-01T00:00:00", periods=n, freq="H", name="datetime")
    return pd.DataFrame({"value": range(n)}, index=idx)


def test_probe_001_hourly_index_should_be_rejected_as_daily():
    # Arrange: deterministic hourly dataframe
    gen_df = _make_hourly_df(8)

    # Create evaluator instance without invoking unknown __init__ logic
    evaluator = evaluators.FactorDatetimeDailyEvaluator.__new__(evaluators.FactorDatetimeDailyEvaluator)

    # Monkeypatch _get_df to return our generated dataframe regardless of inputs.
    # Note: evaluate calls self._get_df(gt_implementation, implementation) so stub accepts (gt_impl, impl)
    evaluator._get_df = lambda gt_impl, impl: (None, gen_df)

    # Act: call the public entrypoint. We pass None for implementation placeholders because our stub ignores them.
    result_msg, verdict = evaluator.evaluate(None, None)

    # Primary oracle: the evaluator should detect sub-day (hourly) spacing and therefore return a non-daily verdict (False)
    assert verdict is False, (
        f"Invariant violated: expected non-daily verdict False for uniform 1-hour spacing, got {verdict}. Message: {result_msg}"
    )

    # Supporting observable assertion: message should indicate non-daily diagnosis
    assert "not daily" in str(result_msg).lower(), (
        f"Expected the returned message to indicate non-daily; got: {result_msg}"
    )
