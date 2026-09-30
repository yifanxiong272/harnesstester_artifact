import pytest

import openhands.io.json as oj


def test_loads_success_nested_round_069(monkeypatch):
    """When the input contains a nested JSON object, loads should extract,
    optionally repair (no-op here) and return the parsed object.
    This exercises the '{' -> depth increment, nested braces, and final json.loads path.
    """
    # input is not a top-level JSON string so the initial json.loads will fail
    s = 'prefix {"a": {"b": 2}} suffix'

    # make repair_json deterministic: return the extracted substring unchanged
    monkeypatch.setattr(oj, "repair_json", lambda resp: resp)

    res = oj.loads(s)
    assert res == {"a": {"b": 2}}


def test_loads_repair_raises_round_069(monkeypatch):
    """If repair_json raises (ValueError/TypeError), loads should raise LLMResponseError
    with the Invalid JSON message. This exercises the exception-handling branch
    inside the extraction block.
    """
    s = 'some text before {not: valid, json,} and after'

    def raising_repair(resp):
        raise ValueError("repair failed")

    monkeypatch.setattr(oj, "repair_json", raising_repair)

    with pytest.raises(oj.LLMResponseError) as excinfo:
        oj.loads(s)

    # ensure the error raised comes from the attempted repair/parse path
    assert "Invalid JSON in response" in str(excinfo.value)


def test_loads_no_json_round_069():
    """When no JSON object braces are present, loads should raise LLMResponseError
    with the 'No valid JSON object found in response.' message. This covers the
    loop-complete -> raise path.
    """
    s = "this string contains no braces at all"

    with pytest.raises(oj.LLMResponseError) as excinfo:
        oj.loads(s)

    assert str(excinfo.value) == "No valid JSON object found in response."
