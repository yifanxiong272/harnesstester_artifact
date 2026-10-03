def test_generated_target_probe_asset_001():
    """Probe: ensure sub-day (hourly) MultiIndex 'datetime' level is classified as non-daily.

    Invariant (conservative): Any adjacent timedelta strictly less than 1 day should lead the evaluator to deem the dataframe non-daily. We assert the evaluator's boolean verdict is False for an hourly-spaced 'datetime' level embedded in a MultiIndex.
    """

    import pandas as pd

    from rdagent.components.coder.factor_coder.CoSTEER import evaluators

    def make_hourly_multiindex_df(start="2020-01-01", periods=6):
        # Single constant outer key to ensure adjacency corresponds to adjacent datetimes
        times = pd.date_range(start=start, periods=periods, freq="H")
        outer = ["const_id"] * len(times)
        mi = pd.MultiIndex.from_arrays([outer, times], names=["id", "datetime"])
        return pd.DataFrame({"v": range(len(times))}, index=mi)

    # Build deterministic hourly MultiIndex dataframe
    gen_df = make_hourly_multiindex_df()

    # Create evaluator instance without invoking its __init__ to avoid external side effects
    cls = evaluators.FactorDatetimeDailyEvaluator
    evaluator = object.__new__(cls)

    # Monkeypatch _get_df to deterministically return our generated dataframe
    # Note: the evaluate method expects _get_df(gt_implementation, implementation)
    evaluator._get_df = lambda gt_impl, impl: (None, gen_df)

    # Call the public entrypoint with dummy Implementation arguments (not used by our _get_df)
    result = evaluator.evaluate(None, None)

    # Basic shape checks on returned value
    assert isinstance(result, tuple), "evaluate must return a tuple"
    assert len(result) >= 2, "evaluate tuple must contain at least two elements (message, verdict)"

    # Primary oracle: the boolean verdict must be False for hourly (sub-day) spacing
    verdict = result[1]
    assert verdict is False, (
        "Invariant violated: hourly-spaced 'datetime' level should be classified as non-daily (False). "
        f"Evaluator returned: {result!r}"
    )
