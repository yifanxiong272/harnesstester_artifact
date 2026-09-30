import pytest
from types import SimpleNamespace

from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler


class ConfigMock:
    def __init__(self, vals: dict, verbosity_level: int = 0):
        self._vals = dict(vals)
        self.verbosity_level = verbosity_level

    def get(self, key, default=None):
        return self._vals.get(key, default)


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str):
        # deterministic recording of message strings
        self.messages.append(str(msg))


class NoCallLogger:
    def info(self, msg: str):
        # Should not be called in tests where verbosity < 2
        raise AssertionError("logger.info was called unexpectedly")


def _make_settings(config_vals, verbosity_level=0):
    return SimpleNamespace(config=ConfigMock(config_vals, verbosity_level=verbosity_level))


def test_valid_configuration_no_verbosity_round_104(monkeypatch):
    # verbosity < 2 so logger.info must NOT be called
    settings = _make_settings({
        "extended_thinking_budget_tokens": 3000,
        "extended_thinking_max_output_tokens": 5000,
    }, verbosity_level=1)

    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings",
        lambda: settings,
    )
    # patch logger to ensure no calls will raise
    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger",
        lambda: NoCallLogger(),
    )

    kwargs = {}
    # call unbound method with a dummy self
    result = LiteLLMAIHandler._configure_claude_extended_thinking(object(), "claude-1", kwargs)

    # assert thinking enabled and numeric values propagated
    assert result["thinking"] == {"type": "enabled", "budget_tokens": 3000}
    assert result["max_tokens"] == 5000
    assert result["temperature"] == 1


def test_valid_configuration_with_verbosity_logging_round_104(monkeypatch):
    # verbosity >= 2 should cause two logger.info calls with expected substrings
    settings = _make_settings({
        "extended_thinking_budget_tokens": 1000,
        "extended_thinking_max_output_tokens": 2000,
    }, verbosity_level=2)

    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings",
        lambda: settings,
    )

    logger = DummyLogger()
    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger",
        lambda: logger,
    )

    kwargs = {}
    res = LiteLLMAIHandler._configure_claude_extended_thinking(object(), "claude-x", kwargs)

    # two info messages expected
    assert len(logger.messages) == 2
    # first message should mention max output tokens and model name
    assert "Adding max output tokens" in logger.messages[0]
    assert "claude-x" in logger.messages[0]
    # second message should mention Temperature
    assert "Temperature may only be set to 1 when thinking is enabled" in logger.messages[1]

    assert res["thinking"]["budget_tokens"] == 1000
    assert res["max_tokens"] == 2000
    assert res["temperature"] == 1


def test_invalid_budget_type_round_104(monkeypatch):
    # budget not an int -> ValueError mentioning the bad value
    settings = _make_settings({
        "extended_thinking_budget_tokens": "not-an-int",
        "extended_thinking_max_output_tokens": 2000,
    }, verbosity_level=0)

    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger",
        lambda: DummyLogger(),
    )

    with pytest.raises(ValueError) as exc:
        LiteLLMAIHandler._configure_claude_extended_thinking(object(), "claude", {})

    assert "extended_thinking_budget_tokens must be a positive integer" in str(exc.value)
    assert "not-an-int" in str(exc.value)


def test_invalid_max_output_type_round_104(monkeypatch):
    # max output not an int -> ValueError mentioning the bad value
    settings = _make_settings({
        "extended_thinking_budget_tokens": 1000,
        "extended_thinking_max_output_tokens": None,
    }, verbosity_level=0)

    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger",
        lambda: DummyLogger(),
    )

    with pytest.raises(ValueError) as exc:
        LiteLLMAIHandler._configure_claude_extended_thinking(object(), "claude", {})

    assert "extended_thinking_max_output_tokens must be a positive integer" in str(exc.value)
    assert "None" in str(exc.value)


def test_max_output_less_than_budget_round_104(monkeypatch):
    # max output less than budget -> ValueError that mentions both numbers
    settings = _make_settings({
        "extended_thinking_budget_tokens": 5000,
        "extended_thinking_max_output_tokens": 1000,
    }, verbosity_level=0)

    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "pr_agent.algo.ai_handlers.litellm_ai_handler.get_logger",
        lambda: DummyLogger(),
    )

    with pytest.raises(ValueError) as exc:
        LiteLLMAIHandler._configure_claude_extended_thinking(object(), "claude", {})

    msg = str(exc.value)
    assert "extended_thinking_max_output_tokens (1000) must be greater than or equal to extended_thinking_budget_tokens (5000)" in msg
