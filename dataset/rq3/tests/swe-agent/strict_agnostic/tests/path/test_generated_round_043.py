import pytest
from unittest.mock import patch
from sweagent.agent.models import HumanThoughtModel, HumanModel

# We will create instances without running __init__ to avoid needing real configs/tools.
# Tests patch builtins.input to simulate user-entered thoughts and patch HumanModel._query
# to return deterministic action strings.

def test_humanthought_immediate_end_round_043():
    # Single input that contains END_THOUGHT immediately -> triggers branch that splits on END_THOUGHT
    inputs = ["I thought immediate END_THOUGHT"]
    expected_thought_all = "I thought immediate "  # text before END_THOUGHT
    expected_action = "ACTION1"
    expected_message = f"{expected_thought_all}\n```\n{expected_action}\n```"

    with patch('builtins.input', side_effect=inputs):
        with patch.object(HumanModel, "_query", return_value=expected_action):
            # instantiate without __init__ to avoid external dependencies
            inst = object.__new__(HumanThoughtModel)
            result = HumanThoughtModel.query(inst, history=[])

    assert isinstance(result, dict)
    assert result.get("message") == expected_message


def test_humanthought_multiline_round_043():
    # Multiple inputs where the END_THOUGHT occurs on the second line -> exercises the loop path
    inputs = ["First line", "Second line END_THOUGHT"]
    # The implementation concatenates thought fragments without adding separators
    expected_thought_all = "First lineSecond line "
    expected_action = "MY_ACTION"
    expected_message = f"{expected_thought_all}\n```\n{expected_action}\n```"

    with patch('builtins.input', side_effect=inputs):
        with patch.object(HumanModel, "_query", return_value=expected_action):
            inst = object.__new__(HumanThoughtModel)
            result = HumanThoughtModel.query(inst, history=None)

    assert isinstance(result, dict)
    assert result["message"] == expected_message
