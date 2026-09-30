import pytest

from gpt_researcher.actions import utils
from gpt_researcher.actions.utils import calculate_cost


class DummyLogger:
    def __init__(self):
        self.messages = []

    def warning(self, msg):
        # mirror the interface used in the module under test
        self.messages.append(msg)


def test_known_model_cost_round_135(monkeypatch):
    """Known model should compute cost without emitting a warning."""
    dummy = DummyLogger()
    # Patch the logger symbol where the function resolves it
    monkeypatch.setattr(utils, "logger", dummy)

    prompt = 100
    completion = 200
    # Mixed-case to exercise the .lower() conversion
    model_input = "GPT-3.5-Turbo"

    result = calculate_cost(prompt, completion, model_input)

    expected_per_1k = 0.002  # from the costs dict in the source
    expected = (prompt + completion) / 1000 * expected_per_1k

    # Use approx for floating-point determinism
    assert result == pytest.approx(expected)
    # Ensure no warning was emitted for a known model
    assert dummy.messages == []


def test_unknown_model_warns_and_returns_default_round_135(monkeypatch):
    """Unknown model should trigger a warning and return the default cost."""
    dummy = DummyLogger()
    monkeypatch.setattr(utils, "logger", dummy)

    prompt = 10
    completion = 5
    model_input = "UnKnOwn-MoDeL"

    result = calculate_cost(prompt, completion, model_input)

    # Default return value for unknown models as implemented in the function
    assert result == pytest.approx(0.0001)

    # Exactly one warning call with the lowered model name should have been recorded
    assert len(dummy.messages) == 1
    expected_lower = model_input.lower()
    expected_message = f"Unknown model: {expected_lower}. Cost calculation may be inaccurate."
    assert dummy.messages[0] == expected_message
