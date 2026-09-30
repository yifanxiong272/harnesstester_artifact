import json
import pytest

import sweagent.tools.parsing as parsing
from sweagent.tools.parsing import JsonParser, FormatError


class Arg:
    def __init__(self, name, argument_format="{{ value }}", required=False):
        self.name = name
        self.argument_format = argument_format
        self.required = required


class SimpleCommand:
    def __init__(self, name, arguments=None, invoke_format="{arg}"):
        self.name = name
        # arguments should be a list of Arg-like objects or falsy
        self.arguments = arguments
        self.invoke_format = invoke_format


def test_non_dict_json_round_006():
    parser = JsonParser()
    # model_response message is JSON array, not an object
    model_response = {"message": json.dumps([1, 2, 3])}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[])
    assert "Model output is not a JSON object." in str(exc.value)


def test_missing_top_level_key_round_006():
    parser = JsonParser()
    # Missing the 'command' key
    model_response = {"message": json.dumps({"thought": "thinking"})}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[])
    assert "Key 'command' is missing from model output." in str(exc.value)


def test_command_not_dict_round_006():
    parser = JsonParser()
    # 'command' is present but not a JSON object
    model_response = {"message": json.dumps({"thought": "t", "command": "not_a_dict"})}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[])
    assert "Value of 'command' key is not a JSON object." in str(exc.value)


def test_missing_name_in_command_round_006():
    parser = JsonParser()
    # 'command' object missing 'name'
    model_response = {"message": json.dumps({"thought": "t", "command": {}})}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[])
    assert "Key 'name' is missing from 'command' object." in str(exc.value)


def test_unknown_command_non_strict_round_006():
    parser = JsonParser()
    # command name 'unknown' not in provided commands; strict=False should return thought and joined string
    payload = {"thought": "t1", "command": {"name": "unknown", "arguments": {"only": "val"}}}
    model_response = {"message": json.dumps(payload)}

    thought, action = parser(model_response, commands=[], strict=False)
    assert thought == "t1"
    # second element should be the command name followed by the single argument value
    assert action == "unknown val"


def test_unknown_command_strict_raises_round_006():
    parser = JsonParser()
    payload = {"thought": "t", "command": {"name": "nope", "arguments": {}}}
    model_response = {"message": json.dumps(payload)}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[], strict=True)
    assert "Command 'nope' not found in list of available commands." in str(exc.value)


def test_command_with_args_and_quoting_round_006(monkeypatch):
    parser = JsonParser()

    # Ensure deterministic quoting behavior: force _should_quote to True so quote() is used
    monkeypatch.setattr(parsing, "_should_quote", lambda value, command: True)

    # Create a command that accepts a single argument 'a1' and will render it
    arg = Arg(name="a1", argument_format="{{ value }}-formatted", required=False)
    cmd = SimpleCommand(name="c1", arguments=[arg], invoke_format="run {a1}")

    payload = {"thought": "ok", "command": {"name": "c1", "arguments": {"a1": "space val"}}}
    model_response = {"message": json.dumps(payload)}

    thought, action = parser(model_response, commands=[cmd], strict=True)
    assert thought == "ok"
    # Expect that the argument was quoted (shlex.quote) then formatted by the template
    # shlex.quote on 'space val' yields "'space val'"
    assert action == "run 'space val'-formatted"


def test_missing_required_arg_strict_round_006():
    parser = JsonParser()
    # Arg 'a_req' is required but missing from payload, strict=True should raise
    arg = Arg(name="a_req", argument_format="{{ value }}", required=True)
    cmd = SimpleCommand(name="need", arguments=[arg], invoke_format="do {a_req}")

    payload = {"thought": "t", "command": {"name": "need", "arguments": {}}}
    model_response = {"message": json.dumps(payload)}

    with pytest.raises(FormatError) as exc:
        parser(model_response, commands=[cmd], strict=True)
    assert "Required argument 'a_req' missing for command 'need'" in str(exc.value)
