from types import SimpleNamespace
from sweagent.tools.parsing import FunctionCallingParser

class _Arg:
    def __init__(self, name: str, required: bool, argument_format: str):
        self.name = name
        self.required = required
        self.argument_format = argument_format

class _Cmd:
    def __init__(self, name: str, arguments, invoke_format: str, end_name=None):
        self.name = name
        self.arguments = arguments
        self.invoke_format = invoke_format
        self.end_name = end_name


def test_probe_001():
    """
    Boundary: boundary-001
    Intent: pass a tool call whose function.arguments is already a dict and assert
    the parser returns the formatted invocation (empty string when argument value is None)
    and does not raise an UnboundLocalError/NameError due to an uninitialized 'values'.
    """
    parser = FunctionCallingParser()

    # Build a tool_call mapping as the model would emit; note we include 'message' and
    # 'tool_calls' to match FunctionCallingParser.__call__'s expected structure.
    tool_call = {"function": {"name": "cmdname", "arguments": {"arg": None}}}
    model_response = {"message": "", "tool_calls": [tool_call]}

    # Create a single required arg whose argument_format renders the 'value' variable.
    arg = _Arg(name="arg", required=True, argument_format="{{value}}")

    # Command invoke_format references the arg by name; end_name left as None.
    cmd = _Cmd(name="cmdname", arguments=[arg], invoke_format="{arg}", end_name=None)

    # Call the public entrypoint (__call__) via the class instance.
    # __call__ returns (message, action) where action is the formatted invocation.
    message, action = parser(model_response, [cmd])

    # Observable assertions: returned action is the rendered invocation and must be the empty string
    # because the argument value was None and get_quoted_arg maps None -> "".
    assert isinstance(action, str)
    assert action == ""  # primary oracle: rendered invocation equals empty string
