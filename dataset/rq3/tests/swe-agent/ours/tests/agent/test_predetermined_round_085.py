import pytest

from sweagent.agent import models
from sweagent.agent.models import PredeterminedTestModel


def test_string_output_calls_handle_and_returns_message_round_085(monkeypatch):
    """When an output is a string, _handle_raise_commands is invoked and the
    returned dict contains the original string under 'message'.
    """
    called = []

    def fake_handle(action):
        called.append(action)

    # Patch the module-level handler where PredeterminedTestModel resolves it
    monkeypatch.setattr(models, "_handle_raise_commands", fake_handle)

    m = PredeterminedTestModel(outputs=["hello world"])

    res = m.query()

    assert res == {"message": "hello world"}
    # ensure the handler was invoked exactly once with the string
    assert called == ["hello world"]


def test_non_str_non_dict_raises_value_error_round_085():
    """If an output is neither str nor dict, PredeterminedTestModel.query
    should raise a ValueError with an informative message including the type.
    """
    m = PredeterminedTestModel(outputs=[42])

    with pytest.raises(ValueError) as excinfo:
        m.query()

    # the message uses the type(...) representation
    assert "Output must be string or dict, got <class 'int'>" in str(excinfo.value)


def test_dict_with_tool_calls_included_round_085():
    """If the output is a dict and contains 'tool_calls', it should appear
    in the result under the same key.
    """
    payload = {"message": "ok", "tool_calls": [{"name": "t", "args": {}}]}
    m = PredeterminedTestModel(outputs=[payload])

    res = m.query()

    assert res["message"] == "ok"
    assert "tool_calls" in res
    # ensure the tool_calls payload is preserved exactly
    assert res["tool_calls"] == payload["tool_calls"]
