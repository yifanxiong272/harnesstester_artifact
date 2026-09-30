import builtins
import sweagent.agent.models as models


def test_human_thought_single_round_041(monkeypatch):
    """Single-input case where the first input contains END_THOUGHT.

    Verifies that the thought is truncated at END_THOUGHT and that the
    action returned from HumanModel._query is wrapped correctly in the
    returned message.
    """
    # Simulate a single input that already contains END_THOUGHT
    inputs = iter(["Alpha END_THOUGHT"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    recorded = {}

    def fake_query(self, history, action_prompt):
        # record what was passed and return a deterministic action
        recorded['history'] = history
        recorded['action_prompt'] = action_prompt
        return "ACTION_SINGLE"

    # Patch the HumanModel._query used by HumanThoughtModel.query
    monkeypatch.setattr(models.HumanModel, "_query", fake_query)

    # Create instance without invoking __init__ to avoid unrelated side effects
    inst = object.__new__(models.HumanThoughtModel)

    res = models.HumanThoughtModel.query(inst, history=None)

    # The thought part before END_THOUGHT should be preserved (including any trailing space)
    assert res == {"message": "Alpha \n```\nACTION_SINGLE\n```"}
    # Ensure the patched _query saw the expected action_prompt
    assert recorded['action_prompt'] == "Action: "


def test_human_thought_multi_round_041(monkeypatch):
    """Multi-input case where the first input lacks END_THOUGHT and the second contains it.

    Verifies concatenation behavior across loop iterations and that history is
    forwarded unchanged to the action query.
    """
    # First input doesn't contain END_THOUGHT, second does (with a leading space)
    inputs = iter(["A", " BEND_THOUGHT"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    recorded = {}

    def fake_query(self, history, action_prompt):
        recorded['history'] = history
        recorded['action_prompt'] = action_prompt
        return "ACTION_MULTI"

    monkeypatch.setattr(models.HumanModel, "_query", fake_query)

    inst = object.__new__(models.HumanThoughtModel)

    history_obj = {"dummy": True}
    res = models.HumanThoughtModel.query(inst, history=history_obj)

    # Expect concatenation: 'A' + ' B' => 'A B'
    assert res == {"message": "A B\n```\nACTION_MULTI\n```"}
    # Ensure history was forwarded to the action query unchanged
    assert recorded['history'] is history_obj
    assert recorded['action_prompt'] == "Action: "
