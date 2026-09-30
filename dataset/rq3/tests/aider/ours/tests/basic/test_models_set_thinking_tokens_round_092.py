from aider.models import Model


def _make_model(name, extra_params=None, parse_val=None):
    """Create a lightweight Model instance without running full __init__.

    We attach a simple parse_token_value implementation on the instance so
    set_thinking_tokens can be exercised deterministically.
    """
    m = Model.__new__(Model)
    m.name = name
    m.extra_params = extra_params
    m.use_temperature = True

    if parse_val is None:
        # Defensive: if the test didn't expect parse_token_value to be called,
        # raise so the test fails deterministically.
        def _parse(value):
            raise AssertionError("parse_token_value was called unexpectedly")
    else:
        def _parse(value):
            return parse_val

    # Attach the function as an instance attribute so set_thinking_tokens will
    # call it as self.parse_token_value(value).
    m.parse_token_value = _parse
    return m


def test_openrouter_sets_reasoning_round_092():
    # openrouter path, extra_params initially None -> should create extra_body
    m = _make_model("openrouter/foo", extra_params=None, parse_val=123)
    m.set_thinking_tokens("any")

    # use_temperature is turned off
    assert m.use_temperature is False

    # extra_body created with reasoning -> max_tokens set
    assert isinstance(m.extra_params, dict)
    assert "extra_body" in m.extra_params
    assert "reasoning" in m.extra_params["extra_body"]
    assert m.extra_params["extra_body"]["reasoning"]["max_tokens"] == 123


def test_openrouter_removes_reasoning_when_zero_round_092():
    # openrouter path, extra_body exists and contains reasoning -> calling with 0 removes reasoning
    starting = {"extra_body": {"reasoning": {"max_tokens": 10}, "keep": True}}
    m = _make_model("openrouter/bar", extra_params=starting, parse_val=0)
    m.set_thinking_tokens("zero")

    # reasoning removed, other keys preserved
    assert "reasoning" not in m.extra_params["extra_body"]
    assert m.extra_params["extra_body"].get("keep") is True


def test_non_openrouter_sets_thinking_round_092():
    # non-openrouter path, extra_params None -> thinking created when tokens > 0
    m = _make_model("gpt-xyz", extra_params=None, parse_val=500)
    m.set_thinking_tokens("any")

    assert isinstance(m.extra_params, dict)
    assert "thinking" in m.extra_params
    assert m.extra_params["thinking"]["type"] == "enabled"
    assert m.extra_params["thinking"]["budget_tokens"] == 500


def test_non_openrouter_removes_thinking_round_092():
    # non-openrouter path, thinking present -> calling with 0 removes it
    starting = {"thinking": {"type": "enabled", "budget_tokens": 50}, "other": 1}
    m = _make_model("gpt-abc", extra_params=starting, parse_val=0)
    m.set_thinking_tokens("zero")

    assert "thinking" not in m.extra_params
    # ensure other keys remain untouched
    assert m.extra_params.get("other") == 1
