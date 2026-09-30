# file: sweagent/tools/parsing.py:72-94
# asked: {"lines": [], "branches": [[89, 93]]}
# gained: {"lines": [], "branches": [[89, 93]]}

import pytest

from sweagent.tools.parsing import ActionParser
from sweagent.tools.commands import Command
from sweagent.exceptions import FormatError


def test_actionparser_returns_message_when_command_valid():
    parser = ActionParser()
    model_response = {"message": "ls -l /tmp"}
    commands = [Command(name="ls", docstring="List directory")]
    result = parser(model_response, commands)
    assert isinstance(result, tuple)
    assert result[0] == model_response["message"]
    assert result[1] == model_response["message"]


def test_actionparser_raises_formaterror_when_first_word_invalid():
    parser = ActionParser()
    model_response = {"message": "unknowncmd arg1 arg2"}
    commands = [Command(name="ls", docstring="List directory"), Command(name="echo", docstring="Echo")]
    with pytest.raises(FormatError) as excinfo:
        parser(model_response, commands)
    assert str(excinfo.value) == "First word in model response is not a valid command."


def test_actionparser_raises_formaterror_when_message_empty_or_whitespace():
    parser = ActionParser()
    # Empty message case -> .split() is falsy and should raise the same FormatError
    for msg in ("", "   "):
        model_response = {"message": msg}
        commands = [Command(name="ls", docstring="List directory")]
        with pytest.raises(FormatError) as excinfo:
            parser(model_response, commands)
        assert str(excinfo.value) == "First word in model response is not a valid command."
