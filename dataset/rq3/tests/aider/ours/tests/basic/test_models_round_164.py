import pytest

from aider.models import Model


def _make_model(name, extra_params):
    # Bypass __init__ to create a lightweight Model instance for unit testing
    m = Model.__new__(Model)
    m.name = name
    m.extra_params = extra_params
    return m


def test_set_reasoning_effort_openrouter_creates_structure_round_164():
    # openrouter path where extra_params is initially falsy (None)
    m = _make_model("openrouter/special", None)
    # Call the method under test
    m.set_reasoning_effort(5)

    # After calling, extra_params should be a dict with nested structure
    assert isinstance(m.extra_params, dict)
    assert "extra_body" in m.extra_params
    assert isinstance(m.extra_params["extra_body"], dict)
    assert m.extra_params["extra_body"]["reasoning"] == {"effort": 5}


def test_set_reasoning_effort_openrouter_merges_existing_extra_body_round_164():
    # openrouter path where extra_params exists and has extra_body with other keys
    initial = {"extra_body": {"preexisting": True}}
    m = _make_model("openrouter/merge_model", initial)

    m.set_reasoning_effort("high")

    # Should preserve preexisting keys and add reasoning entry
    assert m.extra_params is initial
    assert m.extra_params["extra_body"]["preexisting"] is True
    assert m.extra_params["extra_body"]["reasoning"] == {"effort": "high"}


def test_set_reasoning_effort_non_openrouter_sets_reasoning_effort_round_164():
    # non-openrouter path should set "reasoning_effort" directly
    m = _make_model("gpt-4-classic", None)

    m.set_reasoning_effort(0.75)

    assert isinstance(m.extra_params, dict)
    assert "extra_body" in m.extra_params
    assert m.extra_params["extra_body"]["reasoning_effort"] == 0.75


def test_set_reasoning_effort_none_effort_noop_round_164():
    # If effort is None, method should not mutate existing extra_params
    initial = {"extra_body": {"unchanged": 1}}
    m = _make_model("openrouter/nop", initial)

    m.set_reasoning_effort(None)

    # unchanged should remain and reasoning should not be added
    assert m.extra_params is initial
    assert m.extra_params["extra_body"] == {"unchanged": 1}
