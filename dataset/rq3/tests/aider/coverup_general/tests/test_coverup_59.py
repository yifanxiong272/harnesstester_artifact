# file: aider/models.py:823-849
# asked: {"lines": [837, 838, 839, 840, 842, 843, 848, 849], "branches": [[829, 0], [836, 837], [837, 838], [837, 839], [839, 840], [839, 842], [842, 0], [842, 843], [845, 848], [848, 0], [848, 849]]}
# gained: {"lines": [837, 838, 839, 840, 842, 843, 848, 849], "branches": [[829, 0], [836, 837], [837, 838], [837, 839], [839, 840], [839, 842], [842, 843], [845, 848], [848, 849]]}

import pytest
from aider.models import Model


def _new_model_without_init():
    # Create a Model instance without running __init__
    return object.__new__(Model)


def test_set_thinking_tokens_openrouter_add_and_remove():
    m = _new_model_without_init()
    # set initial attributes that set_thinking_tokens expects
    m.name = "openrouter/special-model"
    m.extra_params = None  # exercise the branch that creates extra_params dict
    m.use_temperature = True
    # parse_token_value should be called and return positive number
    m.parse_token_value = lambda v: 1234

    # Call with a non-zero value: should create extra_params and set extra_body.reasoning
    m.set_thinking_tokens("1234")
    assert m.use_temperature is False
    assert isinstance(m.extra_params, dict)
    assert "extra_body" in m.extra_params
    assert "reasoning" in m.extra_params["extra_body"]
    assert m.extra_params["extra_body"]["reasoning"] == {"max_tokens": 1234}

    # Now call with zero to remove the reasoning key
    m.parse_token_value = lambda v: 0
    m.set_thinking_tokens(0)
    # extra_body should still exist but 'reasoning' key should be removed
    assert "extra_body" in m.extra_params
    assert "reasoning" not in m.extra_params["extra_body"]


def test_set_thinking_tokens_non_openrouter_add_and_remove():
    m = _new_model_without_init()
    m.name = "gpt-something"
    m.extra_params = {}  # start with an empty dict
    m.use_temperature = True
    m.parse_token_value = lambda v: 500

    # Set thinking tokens to a positive number: should add 'thinking'
    m.set_thinking_tokens("500")
    assert m.use_temperature is False
    assert "thinking" in m.extra_params
    assert m.extra_params["thinking"] == {"type": "enabled", "budget_tokens": 500}

    # Now set to 0 to remove the thinking key
    m.parse_token_value = lambda v: 0
    m.set_thinking_tokens(0)
    assert "thinking" not in m.extra_params


def test_set_thinking_tokens_none_is_noop_and_does_not_call_parser():
    m = _new_model_without_init()
    m.name = "anything"
    # Set some state that would change if set_thinking_tokens ran
    m.extra_params = {"thinking": {"type": "enabled", "budget_tokens": 999}}
    m.use_temperature = True

    # Make parse_token_value raise if called so we can assert it's not invoked
    def _raise_if_called(value):
        raise RuntimeError("parse_token_value should not be called for None input")

    m.parse_token_value = _raise_if_called

    # Call with None: should be a no-op and not raise
    m.set_thinking_tokens(None)

    # Ensure state unchanged
    assert m.use_temperature is True
    assert m.extra_params == {"thinking": {"type": "enabled", "budget_tokens": 999}}
