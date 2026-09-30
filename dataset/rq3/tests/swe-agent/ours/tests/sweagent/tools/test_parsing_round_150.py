import pytest
from types import SimpleNamespace

from sweagent.tools.parsing import ActionParser
from sweagent.exceptions import FormatError


def test_actionparser_returns_message_when_action_valid_round_150():
    """Valid first word (action) present in commands -> should return the raw message twice."""
    parser = ActionParser()
    model_response = {"message": "  ls -l  "}
    commands = [SimpleNamespace(name="ls")]

    result = parser(model_response, commands, strict=False)

    assert result == (model_response["message"], model_response["message"])


def test_actionparser_raises_formaterror_invalid_action_round_150():
    """First word is not one of the provided command names -> FormatError with exact message."""
    parser = ActionParser()
    model_response = {"message": "unknown --flag"}
    commands = [SimpleNamespace(name="ls"), SimpleNamespace(name="echo")]

    with pytest.raises(FormatError) as excinfo:
        parser(model_response, commands, strict=False)

    assert str(excinfo.value) == "First word in model response is not a valid command."


def test_actionparser_raises_formaterror_empty_message_round_150():
    """Empty or all-whitespace message -> split() falsy -> FormatError."""
    parser = ActionParser()

    for msg in ["", "   "]:
        with pytest.raises(FormatError) as excinfo:
            parser({"message": msg}, [])
        assert str(excinfo.value) == "First word in model response is not a valid command."
