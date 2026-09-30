# file: gpt_researcher/actions/utils.py:62-97
# asked: {"lines": [79, 80, 81, 82, 83, 84, 85, 89, 90, 91, 92, 93, 95, 96, 97], "branches": [[90, 91], [90, 95]]}
# gained: {"lines": [79, 80, 81, 82, 83, 84, 85, 89, 90, 91, 92, 93, 95, 96, 97], "branches": [[90, 91], [90, 95]]}

import pytest

from gpt_researcher.actions import utils
from gpt_researcher.actions.utils import calculate_cost


@pytest.mark.parametrize(
    "prompt,completion,model,expected",
    [
        (100, 300, "gpt-3.5-turbo", 0.0008),  # 400 tokens * 0.002 / 1000
        (1000, 0, "GPT-4", 0.03),             # case-insensitive model name
        (1000, 1000, "o3-mini", (2000 / 1000) * 5e-07),  # very small per-1k cost
        (50, 50, "gpt-4o-mini", (100 / 1000) * 1e-06),   # another tiny cost
    ],
)
def test_calculate_cost_known_models(prompt, completion, model, expected):
    """
    Verify calculate_cost returns the expected numeric cost for known models,
    and that model name matching is case-insensitive.
    """
    result = calculate_cost(prompt, completion, model)
    # Use a tolerance for floating point comparisons
    assert result == pytest.approx(expected, rel=1e-9, abs=0.0)


def test_calculate_cost_unknown_model_logs_warning_and_defaults(monkeypatch):
    """
    Verify that an unknown model triggers a logger.warning call and returns
    the default fallback cost of 0.0001.
    """
    recorded = []

    # Replace the logger.warning function with one that records messages
    def fake_warning(msg, *args, **kwargs):
        recorded.append(msg)

    # monkeypatch the warning method on the module's logger
    monkeypatch.setattr(utils.logger, "warning", fake_warning)

    # Use mixed case to ensure the function lowercases the model name before checking
    result = calculate_cost(123, 456, "Unknown-MODEL")

    assert result == pytest.approx(0.0001)
    # Ensure a warning was logged exactly once and contains the lowercased model name
    assert len(recorded) == 1
    assert "unknown-model" in recorded[0]
    assert "Cost calculation may be inaccurate" in recorded[0]
