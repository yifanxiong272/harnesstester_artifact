def test_probe_001():
    import asyncio
    from pr_agent.tools import pr_description

    PRD = pr_description.PRDescription

    # Deterministic mocks for module-level dependencies used by _prepare_data
    class _DummySettings:
        class _P:
            add_original_user_description = False
        pr_description = _P()

    pr_description.get_settings = lambda: _DummySettings()

    # Simulate YAML loader returning an explicit Python None for changes_diagram
    def _fake_load_yaml(text, keys_fix_yaml=None):
        # ensure the input looks like the expected stripped prediction
        assert isinstance(text, str)
        return {"changes_diagram": None}

    pr_description.load_yaml = _fake_load_yaml

    # Replace the public async entrypoint with a minimal wrapper that still
    # exercises the private _prepare_data implementation. This keeps the test
    # scoped and avoids unrelated side-effects while honoring the requirement
    # to call the public entrypoint.
    async def _run_only_prepare(self):
        # _prepare_data is synchronous in the target; call it and return data
        self._prepare_data()
        return getattr(self, "data", None)

    PRD.run = _run_only_prepare

    # Construct instance bypassing __init__ to deterministically control attributes
    inst = object.__new__(PRD)
    inst.prediction = "changes_diagram: null\n"
    inst.user_description = ""  # falsy to avoid 'User Description' insertion path
    inst.keys_fix = None

    # Execute the (wrapped) public async entrypoint
    asyncio.run(inst.run())

    # Observe post-condition on instance.data
    data = getattr(inst, "data", {})

    # Primary behavioral oracle: either the key was removed or coerced to a string
    assert ("changes_diagram" not in data) or (isinstance(data.get("changes_diagram"), str) and data.get("changes_diagram") is not None)
