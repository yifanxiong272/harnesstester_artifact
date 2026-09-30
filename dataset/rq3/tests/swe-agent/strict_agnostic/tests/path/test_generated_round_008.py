import json
import pytest
import types

import sweagent.tools.parsing as parsing_module
from sweagent.exceptions import FormatError


# Lightweight test doubles to mimic Command and Argument shapes expected by JsonParser
class _Arg:
    def __init__(self, name, argument_format, required=False):
        self.name = name
        self.argument_format = argument_format
        self.required = required


class _Command:
    def __init__(self, name, arguments=None, invoke_format="{0}"):
        # invoke_format should be a str.format template using named args
        self.name = name
        # arguments is an iterable of _Arg
        self.arguments = arguments or []
        # ensure invoke_format is a format string that can accept named placeholders
        self.invoke_format = invoke_format


def _call_parser_and_raise(model_response, commands, strict=False):
    parser = parsing_module.JsonParser()
    return parser(model_response, commands, strict=strict)


def test_non_dict_message_round_008():
    # model_response message is valid JSON but not a JSON object -> FormatError
    model_response = {"message": json.dumps([1, 2, 3])}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [], strict=False)
    assert "Model output is not a JSON object." in str(exc.value)


def test_missing_thought_key_round_008():
    # Valid JSON object but missing 'thought' key
    model_response = {"message": json.dumps({"command": {"name": "x"}})}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [], strict=False)
    assert "Key 'thought' is missing from model output." in str(exc.value)


def test_command_not_dict_round_008():
    # 'command' exists but is not a dict
    model_response = {"message": json.dumps({"thought": "t", "command": "notadict"})}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [], strict=False)
    assert "Value of 'command' key is not a JSON object." in str(exc.value)


def test_missing_name_in_command_round_008():
    # 'command' is a dict but missing required 'name' key
    model_response = {"message": json.dumps({"thought": "t", "command": {}})}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [], strict=False)
    assert "Key 'name' is missing from 'command' object." in str(exc.value)


def test_command_not_found_strict_round_008():
    # Unknown command name and strict=True should raise
    payload = {"thought": "t", "command": {"name": "unknown_cmd"}}
    model_response = {"message": json.dumps(payload)}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [], strict=True)
    assert "Command 'unknown_cmd' not found in list of available commands." in str(exc.value)


def test_command_not_found_non_strict_round_008():
    # Unknown command name and strict=False should return joined name (and args if present)
    payload = {"thought": "thinking", "command": {"name": "not_a_cmd", "arguments": {"a": "1", "b": "2"}}}
    model_response = {"message": json.dumps(payload)}
    result = _call_parser_and_raise(model_response, [], strict=False)
    # Expect thought and the joined string: name + arg values in original order of values()
    assert result[0] == "thinking"
    # joined string must start with command name
    assert result[1].startswith("not_a_cmd")
    # ensure it contains at least one argument value from payload
    assert "1" in result[1]


def test_missing_required_arg_strict_round_008(monkeypatch):
    # Command has a required argument that is missing -> strict=True raises
    cmd = _Command(name="mycmd", arguments=[_Arg(name="arg1", argument_format="{{ value }}", required=True)], invoke_format="do {arg1}")
    payload = {"thought": "t", "command": {"name": "mycmd", "arguments": {}}}
    model_response = {"message": json.dumps(payload)}
    with pytest.raises(FormatError) as exc:
        _call_parser_and_raise(model_response, [cmd], strict=True)
    assert "Required argument 'arg1' missing for command 'mycmd'" in str(exc.value)


def test_argument_format_and_quoting_round_008(monkeypatch):
    # When _should_quote returns True, the value should be passed through quote() before templating
    # Monkeypatch the parser's internal _should_quote to be deterministic
    monkeypatch.setattr(parsing_module, "_should_quote", lambda value, command: True)

    # Argument formatting uses Jinja2 Template; we assert the template receives the quoted value
    cmd = _Command(
        name="cmdq",
        arguments=[_Arg(name="arg1", argument_format="{{ value }}_end", required=False)],
        invoke_format="do {arg1}"
    )
    payload = {"thought": "t", "command": {"name": "cmdq", "arguments": {"arg1": "needs quoting"}}}
    model_response = {"message": json.dumps(payload)}

    thought, action = _call_parser_and_raise(model_response, [cmd], strict=True)
    assert thought == "t"
    # shlex.quote on a string with a space typically wraps it in single quotes
    # The template appends _end, so ensure that piece is present
    assert action.endswith("_end")
    assert "needs quoting" in action
    # Ensure the returned action uses the invocation format
    assert action.startswith("do ")


def test_no_arguments_uses_invoke_format_round_008():
    # Command with no declared arguments should still use its invoke_format
    cmd = _Command(name="noargs", arguments=[], invoke_format="run-tool")
    payload = {"thought": "t", "command": {"name": "noargs", "arguments": {}}}
    model_response = {"message": json.dumps(payload)}
    thought, action = _call_parser_and_raise(model_response, [cmd], strict=True)
    assert thought == "t"
    assert action == "run-tool"
