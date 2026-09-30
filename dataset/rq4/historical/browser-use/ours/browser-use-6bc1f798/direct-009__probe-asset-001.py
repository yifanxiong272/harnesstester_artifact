def test_probe_001():
    """Probe: feed a BaseMessage-like object whose .content is a list with a code-fenced JSON string

    This monkeypatches the module-level BaseMessage symbol so isinstance checks inside
    the target function treat our object as a BaseMessage. The payload includes an initial
    language hint line ('json\n') and trailing HTML-like noise after the closing brace to
    exercise the code-path that strips tags after parsing.
    """
    # Import the module that exposes the target entrypoint
    import browser_use.agent.message_manager.utils as utils

    # Create a local BaseMessage-like class and assign it to the module symbol so
    # isinstance(obj, BaseMessage) inside the function returns True.
    class LocalBaseMessage:
        def __init__(self, content):
            # content should be a list whose first element is the code-fenced JSON
            self.content = content

    # Monkeypatch the module-level BaseMessage symbol deterministically
    utils.BaseMessage = LocalBaseMessage

    # Code-fenced JSON with language hint and trailing HTML-like tag/noise
    payload = """```json
{"foo": "bar"}
</function>"""

    # Construct the message as required: .content is a list with the payload as first item
    msg = LocalBaseMessage([payload])

    # Call the selected entrypoint
    result = utils.extract_json_from_model_output(msg)

    # Primary behavioral oracle: the function should return the parsed JSON as a dict
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result == {"foo": "bar"}, f"Parsed JSON did not match expected: {result}"
