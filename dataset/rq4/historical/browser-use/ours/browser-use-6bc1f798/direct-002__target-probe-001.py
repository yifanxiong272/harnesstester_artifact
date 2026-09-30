def test_probe_001():
    import importlib

    # Local dummy class to emulate the module's BaseMessage contract
    class DummyBaseMessage:
        def __init__(self, content):
            self.content = content

    # Import the target module and monkeypatch its BaseMessage symbol so
    # isinstance(content, BaseMessage) evaluates to True inside the function.
    utils = importlib.import_module('browser_use.agent.message_manager.utils')
    setattr(utils, 'BaseMessage', DummyBaseMessage)

    # Construct the BaseMessage-like input with a code-block-wrapped JSON payload
    msg = DummyBaseMessage('```json\n{"x": 1, "y": "z"}\n```')

    # Invoke the selected entrypoint directly; preserve original parsing flow
    result = utils.extract_json_from_model_output(msg)

    # Primary behavioral oracle: parsed JSON dict is returned and equals expected
    assert isinstance(result, dict), f'Expected dict, got {type(result)}'
    assert result == {'x': 1, 'y': 'z'}
