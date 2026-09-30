import json
from types import SimpleNamespace

from browser_use.agent.views import AgentHistoryList


class DummyAction:
    """Minimal stand-in for an action object expected by agent_steps.

    Must implement model_dump(exclude_none=True, mode='json') and return
    a JSON-serializable mapping.
    """

    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, exclude_none=True, mode="json"):
        # preserve the contract the production code expects
        assert exclude_none is True
        assert mode == "json"
        return self.payload


def _call_agent_steps_with_history(history):
    """Call the unbound AgentHistoryList.agent_steps with a lightweight self.

    This avoids constructing the full pydantic model while exercising the
    real logic in agent_steps. The lightweight self just needs a .history
    attribute that is iterable and whose items have the attributes used in
    the function under test.
    """
    dummy_self = SimpleNamespace(history=history)
    return AgentHistoryList.agent_steps(dummy_self)


def test_agent_steps_with_actions_and_results_round_120():
    # History item with an action and a single result that has both
    # extracted_content and an error -> both branches for result are covered.
    action_payload = {"name": "click", "params": {"x": 1}}
    action_obj = DummyAction(action_payload)
    model_output = SimpleNamespace(action=[action_obj])

    # result carries extracted_content and an error object
    result_obj = SimpleNamespace(extracted_content="OK", error=Exception("failed"))

    hist_item = SimpleNamespace(model_output=model_output, result=[result_obj])

    steps = _call_agent_steps_with_history([hist_item])

    # Basic structure and content assertions to ensure branches executed
    assert isinstance(steps, list) and len(steps) == 1
    step_text = steps[0]
    assert step_text.startswith("Step 1:\n")

    # Actions serialization should appear and include the action name
    assert "Actions:" in step_text
    # JSON produced by json.dumps should include the key and value
    assert '"name": "click"' in step_text

    # Both result content and error lines should be present
    assert "Result 1: OK" in step_text
    assert "Error 1: failed" in step_text


def test_agent_steps_handles_empty_action_and_no_result_items_round_120():
    # History item where model_output.action is an empty list -> actions branch skipped
    model_output_empty = SimpleNamespace(action=[])
    result_empty_item = SimpleNamespace(extracted_content=None, error=None)
    hist_item_with_empty_action = SimpleNamespace(model_output=model_output_empty, result=[result_empty_item])

    # History item with no model_output and no results -> both branches skipped
    hist_item_no_output = SimpleNamespace(model_output=None, result=[])

    steps = _call_agent_steps_with_history([hist_item_with_empty_action, hist_item_no_output])

    # Each history item should produce a step header even when nothing else is added
    assert len(steps) == 2
    assert steps[0] == "Step 1:\n"
    assert steps[1] == "Step 2:\n"
