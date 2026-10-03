def test_probe_001():
    import pandas as pd
    from rdagent.components.coder.factor_coder.CoSTEER.evaluators import FactorDatetimeDailyEvaluator

    # Build deterministic timestamps spaced by 23 hours 59 minutes (just under 1 day)
    start = pd.Timestamp("2020-01-01T00:00:00")
    step = pd.Timedelta(hours=23, minutes=59)
    timestamps = [start + i * step for i in range(4)]

    # Use a single-level MultiIndex named 'datetime' so get_level_values('datetime') works
    idx = pd.MultiIndex.from_arrays([timestamps], names=["datetime"])
    gen_df = pd.DataFrame({"value": list(range(len(timestamps)))}, index=idx)

    # Create evaluator instance without running its initializer to avoid unknown __init__ requirements
    evaluator = object.__new__(FactorDatetimeDailyEvaluator)

    # Monkeypatch _get_df to deterministically return our prepared dataframe
    def _get_df(gt_implementation, implementation):
        return None, gen_df

    evaluator._get_df = _get_df

    # Call the public entrypoint under test
    result = evaluator.evaluate(None, None)

    # Validate shape of result and assert the independent oracle: gaps < 1 day must be classified non-daily
    assert isinstance(result, tuple), f"evaluate should return a tuple, got: {type(result)!r}"
    msg, ok = result

    # Primary behavioral oracle: the evaluator should mark the near-daily (23h59m) series as non-daily
    assert ok is False, f"Expected non-daily (False) for 23h59m gaps, but got {ok}. Message: {msg}"
