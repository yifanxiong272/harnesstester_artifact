import json
import importlib
import types
import pytest

# Import the module under test
parsing = importlib.import_module("sweagent.tools.parsing")

# Make quoting deterministic for the tests: always do not quote values
parsing._should_quote = lambda value, command: False


def _make_arg(name, required=False, fmt="{{ value }}"):
    return types.SimpleNamespace(name=name, required=required, argument_format=fmt)


def _make_command(name, args, end_name=None, invoke_format="run {foo}"):
    return types.SimpleNamespace(name=name, arguments=args, end_name=end_name, invoke_format=invoke_format)


def test_missing_arg_round_058():
    """
    Exercise the branch where required arguments are missing -> raises FunctionCallingFormatError
    Targets branch: 407->408 and lines 408-409.
    """
    parser = parsing.FunctionCallingParser()

    # Command expects a required argument 'foo'
    cmd = _make_command("cmd_missing", [_make_arg("foo", required=True)], end_name=None, invoke_format="run {foo}")

    # tool_call contains JSON string that does not include 'foo'
    tool_call = {"function": {"name": "cmd_missing", "arguments": json.dumps({"bar": "1"})}}

    with pytest.raises(parsing.FunctionCallingFormatError) as excinfo:
        parser._parse_tool_call(tool_call, [cmd])

    # Assert the exception is about missing required argument(s)
    assert "Required argument(s) missing" in str(excinfo.value)


def test_unexpected_arg_round_058():
    """
    Exercise the branch where extra/unexpected arguments are present -> raises FunctionCallingFormatError
    Targets branch: 415->416 and line 416-417.
    """
    parser = parsing.FunctionCallingParser()

    # Command only defines 'foo' as an allowed argument
    cmd = _make_command("cmd_unexpected", [_make_arg("foo", required=False)], end_name=None, invoke_format="run {foo}")

    # tool_call provides an extra argument 'extra' which is not valid
    tool_call = {"function": {"name": "cmd_unexpected", "arguments": json.dumps({"foo": "1", "extra": "x"})}}

    with pytest.raises(parsing.FunctionCallingFormatError) as excinfo:
        parser._parse_tool_call(tool_call, [cmd])

    assert "Unexpected argument(s): extra" in str(excinfo.value)


def test_extra_arg_ignored_end_name_round_058():
    """
    When the command defines an end_name that matches an extra argument, that extra argument
    should be discarded and no exception raised; the final invocation string should be returned.
    Targets branch: 412->414 (discarding end_name) and the normal successful return path.
    """
    parser = parsing.FunctionCallingParser()

    # Command defines 'foo' and considers 'end' as the end_name that may be present in values
    cmd = _make_command("cmd_endname", [_make_arg("foo", required=False)], end_name="end", invoke_format="run {foo}")

    # Include both the valid 'foo' and the model-inserted 'end' argument which should be ignored
    tool_call = {"function": {"name": "cmd_endname", "arguments": json.dumps({"foo": "1", "end": "STOP"})}}

    result = parser._parse_tool_call(tool_call, [cmd])

    # The discard of the end_name should allow successful formatting and invocation
    assert result == "run 1"
