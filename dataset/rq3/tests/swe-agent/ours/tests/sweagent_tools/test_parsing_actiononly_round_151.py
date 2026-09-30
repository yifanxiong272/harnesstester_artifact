import pytest

from sweagent.tools.parsing import ActionOnlyParser


def test_actiononlyparser_returns_message_round_151():
    """When model_response contains a 'message' key, the parser should
    return an empty string and the message value unchanged.
    """
    parser = ActionOnlyParser()
    message_payload = {"name": "do_something", "args": {"x": 1}}
    model_response = {"message": message_payload}

    result = parser(model_response, [])

    assert isinstance(result, tuple)
    assert result == ("", message_payload)


def test_actiononlyparser_missing_message_raises_keyerror_round_151():
    """If 'message' is not present in model_response, a KeyError should be raised.
    """
    parser = ActionOnlyParser()
    model_response = {"unexpected": "value"}

    with pytest.raises(KeyError):
        parser(model_response, [])
