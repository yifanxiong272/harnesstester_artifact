# file: sweagent/agent/models.py:507-526
# asked: {"lines": [521, 522], "branches": [[520, 521], [524, 526]]}
# gained: {"lines": [521, 522], "branches": [[520, 521]]}

import pytest

from sweagent.agent.models import PredeterminedTestModel


def test_query_raises_on_invalid_output_type():
    # Provide an output that is neither str nor dict (e.g., an int) to trigger the ValueError path.
    model = PredeterminedTestModel(outputs=[123])
    with pytest.raises(ValueError) as excinfo:
        model.query()
    # Ensure the error message matches expectation (exact type representation)
    assert "Output must be string or dict" in str(excinfo.value)
    assert "int" in str(excinfo.value)


def test_query_passes_through_tool_calls_in_dict_output():
    # Provide a dict output that includes "message" and "tool_calls" to exercise that branch.
    tool_calls = [{"name": "tool1", "args": {"x": 1}}, {"name": "tool2", "args": {"y": 2}}]
    outputs = [{"message": "ok", "tool_calls": tool_calls}]
    model = PredeterminedTestModel(outputs=outputs)
    result = model.query()
    # Verify the returned structure contains both message and tool_calls unchanged.
    assert isinstance(result, dict)
    assert result["message"] == "ok"
    assert "tool_calls" in result
    assert result["tool_calls"] is tool_calls or result["tool_calls"] == tool_calls
