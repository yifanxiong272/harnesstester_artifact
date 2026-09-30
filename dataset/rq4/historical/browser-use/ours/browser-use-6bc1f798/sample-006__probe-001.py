def test_probe_001_raises_attribute_error_for_dict_content():
    """Probe whether extract_json_from_model_output incorrectly calls string methods on a dict held in BaseMessage.content.

    The test monkeypatches the module-level BaseMessage symbol to a simple local class so isinstance checks succeed,
    constructs an instance whose .content is a native dict, and asserts that the public entrypoint raises AttributeError.
    """
    from browser_use.agent.message_manager import utils
    import pytest

    # Local minimal BaseMessage-like class matching the public name used by the function
    class DummyBaseMessage:
        def __init__(self, content):
            self.content = content

    # Preserve and restore any existing symbol to avoid surprising global state interference
    orig_BaseMessage = getattr(utils, "BaseMessage", None)
    try:
        utils.BaseMessage = DummyBaseMessage
        # Deterministic input: BaseMessage-like object with native dict content
        msg = DummyBaseMessage({"a": 1})
        # The probe expects the buggy implementation to attempt string operations on the dict
        with pytest.raises(AttributeError):
            utils.extract_json_from_model_output(msg)
    finally:
        # Restore original symbol (or remove the injected one) to keep test side-effects bounded
        if orig_BaseMessage is None:
            try:
                delattr(utils, "BaseMessage")
            except Exception:
                # If deletion fails for any reason, leave best-effort restoration
                pass
        else:
            utils.BaseMessage = orig_BaseMessage
