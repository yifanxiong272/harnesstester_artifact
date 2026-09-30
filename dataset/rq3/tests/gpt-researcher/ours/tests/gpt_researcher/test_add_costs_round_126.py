import pytest

from gpt_researcher.agent import GPTResearcher


def make_shallow_researcher():
    """Create a GPTResearcher instance without running its __init__ to avoid expensive side-effects.

    Returns an object with only the attributes required by add_costs.
    """
    r = object.__new__(GPTResearcher)
    # minimal deterministic state required by add_costs
    r.research_costs = 0.0
    r.step_costs = {}
    r._current_step = "unnamed"
    r.log_handler = None
    return r


def test_add_costs_accumulates_and_step_update_round_126():
    r = make_shallow_researcher()
    # patch class-level _log_event to a stub so any accidental calls are captured
    called = []

    def fake_log_event(self, *args, **kwargs):
        called.append((args, kwargs))

    GPTResearcher._log_event = fake_log_event

    # set current step and add a float cost
    r._current_step = "step_alpha"
    r.log_handler = None  # falsy => logging branch should be skipped

    r.add_costs(1.5)

    assert r.research_costs == pytest.approx(1.5)
    assert r.step_costs["step_alpha"] == pytest.approx(1.5)
    # _log_event must not have been invoked when log_handler is falsy
    assert called == []

    # adding an integer cost accumulates correctly
    r.add_costs(2)
    assert r.research_costs == pytest.approx(3.5)
    assert r.step_costs["step_alpha"] == pytest.approx(3.5)


def test_add_costs_with_log_handler_invokes_log_event_round_126():
    r = make_shallow_researcher()
    r._current_step = "step_beta"
    r.log_handler = object()  # truthy to select logging branch

    captured = {}

    def spy_log_event(self, *args, **kwargs):
        # record positional and keyword arguments for assertions
        captured["args"] = args
        captured["kwargs"] = kwargs

    # Patch on the class so add_costs' attribute lookup resolves to our spy
    GPTResearcher._log_event = spy_log_event

    r.add_costs(4.25)

    assert r.research_costs == pytest.approx(4.25)
    assert r.step_costs["step_beta"] == pytest.approx(4.25)

    # Verify the logging call structure
    # first positional argument should be the event_type string 'research'
    assert "args" in captured and captured["args"]
    assert captured["args"][0] == "research"

    # kwargs should include step and details
    assert "kwargs" in captured and "step" in captured["kwargs"]
    assert captured["kwargs"]["step"] == "cost_update"
    assert "details" in captured["kwargs"] and isinstance(captured["kwargs"]["details"], dict)

    details = captured["kwargs"]["details"]
    assert details["cost"] == 4.25
    assert details["total_cost"] == pytest.approx(r.research_costs)
    assert details["step_name"] == "step_beta"


def test_add_costs_invalid_type_raises_round_126():
    r = make_shallow_researcher()
    with pytest.raises(ValueError) as exc:
        r.add_costs("not-a-number")
    assert "Cost must be an integer or float" in str(exc.value)
