import pytest

from sweagent.tools.parsing import FunctionCallingParser


def test_probe_001():
    """When tool call arguments JSON-decode to a non-dict (list or null), the parser should raise a FunctionCallingFormatError.

    This test constructs a minimal command-like object with one required argument so the parser will attempt to call .keys() on the decoded value if it proceeds. We assert the raised exception's class name is 'FunctionCallingFormatError'.
    """
    parser = FunctionCallingParser()

    class Arg:
        def __init__(self, name, required, argument_format="{value}"):
            self.name = name
            self.required = required
            self.argument_format = argument_format

    class DummyCommand:
        def __init__(self):
            self.name = "cmd"
            # one required argument so parser will rely on .keys()
            self.arguments = [Arg("x", True)]
            self.end_name = None
            self.invoke_format = "{x}"

    commands = [DummyCommand()]

    for bad_json in ("[]", "null"):
        model_response = {
            "message": "testing",
            "tool_calls": [
                {"function": {"name": "cmd", "arguments": bad_json}}
            ],
        }
        with pytest.raises(Exception) as excinfo:
            parser(model_response, commands)
        # Primary observable: raised exception should be the public parsing error type
        assert (
            excinfo.value.__class__.__name__ == "FunctionCallingFormatError"
        ), f"expected FunctionCallingFormatError for arguments={bad_json!r}, got {excinfo.value.__class__.__name__}: {excinfo.value}"
