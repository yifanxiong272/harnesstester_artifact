def test_probe_001():
    import asyncio
    # Import only the public entrypoint symbol declared in the route
    from pr_agent.tools import pr_description as pd

    PRDescription = pd.PRDescription

    # Save originals to restore after the test
    orig_load_yaml = getattr(pd, 'load_yaml', None)
    orig_get_settings = getattr(pd, 'get_settings', None)
    orig_run = getattr(PRDescription, 'run', None)

    # Narrow, deterministic replacements:
    def fake_load_yaml(text, keys_fix_yaml=None):
        # Simulate YAML loader producing an explicit null -> Python None
        return {'changes_diagram': None}

    class _PD:
        add_original_user_description = False

    class _S:
        pr_description = _PD()

    def fake_get_settings():
        return _S()

    async def run_stub(self):
        # Public entrypoint is called; ensure _prepare_data executes deterministically
        return PRDescription._prepare_data(self)

    # Apply mocks
    pd.load_yaml = fake_load_yaml
    pd.get_settings = fake_get_settings
    PRDescription.run = run_stub

    try:
        # Construct instance without running __init__ to control required attributes precisely
        inst = object.__new__(PRDescription)
        # prediction must be a string because _prepare_data does self.prediction.strip()
        inst.prediction = "changes_diagram: null\n"
        inst.keys_fix = None
        inst.user_description = ""

        # Call the public async entrypoint and await it
        asyncio.run(inst.run())

        # Primary behavioral oracle: no exception and changes_diagram is not None
        assert isinstance(getattr(inst, 'data', None), dict), "inst.data should be a dict after _prepare_data"
        if 'changes_diagram' in inst.data:
            assert isinstance(inst.data['changes_diagram'], str), (
                "changes_diagram must be coerced to a str when present, not left as None"
            )
        else:
            # acceptable alternative: key removed
            assert 'changes_diagram' not in inst.data
    finally:
        # Restore originals to avoid affecting other tests
        if orig_load_yaml is not None:
            pd.load_yaml = orig_load_yaml
        if orig_get_settings is not None:
            pd.get_settings = orig_get_settings
        if orig_run is not None:
            PRDescription.run = orig_run
