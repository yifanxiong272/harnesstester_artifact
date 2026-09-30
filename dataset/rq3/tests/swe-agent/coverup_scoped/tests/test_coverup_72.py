# file: sweagent/tools/parsing.py:97-106
# asked: {"lines": [106], "branches": []}
# gained: {"lines": [106], "branches": []}

import pytest

from sweagent.tools.parsing import ActionOnlyParser


def test_action_only_parser_returns_message():
    parser = ActionOnlyParser()  # pydantic model with defaults
    model_response = {"message": "do_something"}
    result = parser(model_response, commands=[])
    assert isinstance(result, tuple)
    assert result == ("", "do_something")


def test_action_only_parser_missing_message_raises_keyerror():
    parser = ActionOnlyParser()
    with pytest.raises(KeyError):
        parser({}, commands=[])
