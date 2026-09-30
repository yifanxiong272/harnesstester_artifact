import json
import re
from openhands.llm.fn_call_converter import convert_tool_call_to_string


def test_probe_001():
    # Build deterministic arguments: a parameter whose value is a nested object and array
    nested = {"nested": "value", "arr": [1, "two"], "flag": True}
    args = {"param1": nested}

    tool_call = {
        "id": "test-id-001",
        "type": "function",
        "function": {
            "name": "myfunc",
            "arguments": json.dumps(args)
        }
    }

    out = convert_tool_call_to_string(tool_call)

    # Locate the parameter block for param1
    m = re.search(r"<parameter=param1>(.*?)</parameter>", out, re.S)
    assert m is not None, f"Missing <parameter=param1> block in output: {out!r}"
    content = m.group(1).strip()

    # PRIMARY ORACLE: nested object must be serialized using JSON double quotes
    # This checks for a representative substring that would only appear with JSON double-quoted serialization
    assert '"nested": "value"' in content, (
        "Expected nested object to be emitted with JSON double quotes (e.g. \"nested\": \"value\").\n"
        f"Actual parameter content: {content!r}"
    )
