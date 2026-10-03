def test_probe_001():
    import pandas as pd
    from rdagent.components.coder.factor_coder.CoSTEER import evaluators

    # Prepare an hourly datetime index named 'datetime'
    idx = pd.date_range(start="2021-01-01 00:00", periods=6, freq="H")
    idx = idx.rename("datetime")
    gen_df = pd.DataFrame({"val": range(len(idx))}, index=idx)

    # Obtain the unbound evaluate function from the class so we can call it with a lightweight dummy self.
    evaluate_func = evaluators.FactorDatetimeDailyEvaluator.evaluate

    # Dummy self that provides the _get_df(gt_implementation, implementation) used by evaluate
    class DummySelf:
        pass

    dummy = DummySelf()
    # _get_df is expected to be called as _get_df(gt_implementation, implementation)
    dummy._get_df = lambda gt_impl, impl: (None, gen_df)

    # Call the evaluator entrypoint with both implementation arguments as None (they are forwarded to _get_df)
    result = evaluate_func(dummy, None, None)

    # Primary behavioral oracle: evaluator must mark hourly data as not daily
    assert isinstance(result, tuple), "evaluate should return a tuple"
    message, is_daily = result
    assert is_daily is False, f"Expected evaluator to mark hourly data as not daily, got {result}"
    assert "not daily" in str(message).lower(), f"Expected message to indicate non-daily, got: {message}"
