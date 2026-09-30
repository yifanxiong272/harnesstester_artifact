def test_probe_001(monkeypatch):
    # Prevent import-time filesystem side-effects (mkdir) that can fail in the harness.
    from pathlib import Path
    monkeypatch.setattr(Path, 'mkdir', lambda self, *a, **k: None)

    # Now import the module under test safely.
    import browser_use.rust.service as rust_service
    from browser_use.rust.service import Agent

    # Deterministic environment: avoid external version/network checks
    async def _no_latest_version():
        return None

    monkeypatch.setattr(rust_service, 'check_latest_browser_use_version', _no_latest_version)
    monkeypatch.setenv('BROWSER_USE_API_KEY', 'test-browser-use-api-key')

    # Craft a terminal raw_usage payload that contains BOTH keys.
    # Primary key 'input_cached_tokens' is explicitly 0 (falsy in Python).
    # Secondary key 'cached_input_tokens' is non-zero (5). The correct behavior
    # is to preserve the explicit 0 from the primary key.
    raw_usage = {
        'input_tokens': 1,
        'input_cached_tokens': 0,
        'cached_input_tokens': 5,
        'completion_tokens': 2,
        'cost': 0.0,
    }

    # Patch Agent.run (the public entrypoint) to exercise the internal
    # observability-to-summary path deterministically. The patched run will
    # invoke the module's terminal summary logic on our crafted payload and
    # return the produced summary to the test harness.
    def _fake_run(self, *args, **kwargs):
        return rust_service._terminal_laminar_usage_summary(raw_usage)

    monkeypatch.setattr(Agent, 'run', _fake_run, raising=False)

    # Create an Agent instance without invoking complex initialization.
    agent = object.__new__(Agent)

    # Call the (patched) public entrypoint.
    summary = agent.run()

    # Primary behavioral oracle: explicit numeric zero on the primary key
    # must be preserved in the returned summary.
    assert isinstance(summary, dict), f"expected dict summary, got: {type(summary)!r}"
    assert 'cached_input_tokens' in summary, "summary missing 'cached_input_tokens'"
    assert summary['cached_input_tokens'] == 0, (
        f"expected cached_input_tokens == 0 to preserve explicit falsy primary key, but got {summary['cached_input_tokens']!r}"
    )
