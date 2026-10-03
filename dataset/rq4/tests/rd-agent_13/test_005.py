def test_probe_001():
    """Probe: a DatetimeIndex with 1-second adjacent deltas must be classified non-daily.

    Invariant: any sequence of timestamps with adjacent differences strictly less than one day
    (here 1 second) should be considered non-daily. We build a minimal DataFrame with such an
    index and stub the evaluator's _get_df to return it. The test fails if the evaluator
    returns a daily (True) verdict.
    """

    import pandas as pd

    # Local helper: build a DataFrame with a DatetimeIndex named 'datetime' and 1-second spacing
    def _make_1s_spaced_df():
        # deterministic timestamps
        idx = pd.date_range(start="2020-01-01 00:00:00", periods=3, freq="S")
        # ensure index has the explicit name the evaluator checks for
        idx = idx.rename("datetime")
        df = pd.DataFrame({"val": [0, 1, 2]}, index=idx)
        return df

    # Import only the declared public entrypoint class
    from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator

    gen_df = _make_1s_spaced_df()

    # Create an instance without invoking __init__ to avoid unknown constructor requirements
    evaluator = FactorDatetimeDailyEvaluator.__new__(FactorDatetimeDailyEvaluator)

    # Monkeypatch the instance method _get_df to deterministically return (_, gen_df).
    # The real evaluate calls self._get_df(gt_implementation, implementation) so our stub
    # should accept exactly two positional args (gt_impl, impl).
    evaluator._get_df = lambda gt_impl, impl: (None, gen_df)

    # Call evaluate with dummy arguments (None). Signature is (implementation, gt_implementation)
    result = evaluator.evaluate(None, None)

    # External observable assertion: result must be a tuple and second element must be False
    assert isinstance(result, tuple), f"evaluate should return a tuple, got: {type(result)!r}"
    # Primary oracle: reject sub-day (1-second) spacing as daily
    assert result[1] is False, (
        "Invariant violated: a series with 1-second adjacent deltas was not classified as non-daily. "
        f"evaluate returned: {result!r}"
    )
