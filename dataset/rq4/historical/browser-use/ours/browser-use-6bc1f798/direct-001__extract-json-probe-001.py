def test_probe_001():
    import importlib

    # Import the target module (only the declared public route is used)
    mod = importlib.import_module("browser_use.agent.message_manager.utils")

    # Save original BaseMessage symbol if present so we can restore it
    orig_base = getattr(mod, "BaseMessage", None)

    # Deterministic dummy class to satisfy isinstance checks in the target function
    class DummyBaseMessage:
        def __init__(self, content):
            self.content = content

    try:
        # Monkeypatch the module's BaseMessage so isinstance(msg, BaseMessage) is True
        mod.BaseMessage = DummyBaseMessage

        # Create a message whose content is a code-block-wrapped JSON string
        msg = DummyBaseMessage('```json\n{"k":"v"}```')

        # Call the entrypoint under test
        result = mod.extract_json_from_model_output(msg)

        # Primary oracle: the function should return the parsed dict
        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        assert result == {"k": "v"}, f"Parsed JSON did not match expected dict: {result}"
    finally:
        # Restore original symbol to avoid leaking the monkeypatch
        if orig_base is None:
            try:
                delattr(mod, "BaseMessage")
            except Exception:
                # If deletion fails for any reason, set to None to avoid lingering incorrect state
                mod.BaseMessage = None
        else:
            mod.BaseMessage = orig_base
