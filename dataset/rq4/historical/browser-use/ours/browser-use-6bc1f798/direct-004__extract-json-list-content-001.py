def test_probe_001():
    """Probe: pass a BaseMessage-like object whose .content is a list with a JSON string as first element.

    This test monkeypatches the module-level BaseMessage symbol to a minimal stand-in so
    isinstance checks inside extract_json_from_model_output take the intended branch.
    It then restores the original symbol to avoid persistent side effects.
    """
    # Import only the declared module/entrypoint and operate via its namespace
    from browser_use.agent.message_manager import utils

    # Prepare a lightweight stand-in class for BaseMessage so isinstance(...) succeeds
    class _FakeBaseMessage:
        def __init__(self, content):
            self.content = content

    # Record original and replace in module namespace
    original_exists = hasattr(utils, 'BaseMessage')
    original = getattr(utils, 'BaseMessage', None)
    utils.BaseMessage = _FakeBaseMessage

    try:
        # Construct the BaseMessage-like object whose .content is a list and first element is a JSON string
        msg = _FakeBaseMessage(['{"foo": "bar"}'])

        # Call the target entrypoint
        result = utils.extract_json_from_model_output(msg)

        # Primary behavioral oracle: the parsed dict must equal the expected mapping
        assert result == {'foo': 'bar'}
    finally:
        # Restore the original BaseMessage symbol to avoid affecting other tests
        if original_exists:
            utils.BaseMessage = original
        else:
            # remove the attribute we added
            try:
                delattr(utils, 'BaseMessage')
            except Exception:
                # If deletion fails for some unexpected reason, set it back to original safe value
                utils.BaseMessage = original
