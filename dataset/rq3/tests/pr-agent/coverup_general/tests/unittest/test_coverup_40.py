# file: pr_agent/tools/pr_code_suggestions.py:670-734
# asked: {"lines": [673, 674, 675, 676, 677, 678, 691, 692, 693, 694, 695, 709, 710, 711, 712, 724, 725, 726, 727, 728, 729, 732, 733], "branches": [[672, 673], [689, 691], [697, 732], [702, 709], [710, 711], [710, 714], [716, 715], [721, 724]]}
# gained: {"lines": [673, 674, 675, 676, 677, 678, 691, 692, 693, 694, 695, 709, 710, 711, 712, 724, 725, 726, 727, 728, 729, 732, 733], "branches": [[672, 673], [689, 691], [697, 732], [702, 709], [710, 711], [710, 714], [716, 715], [721, 724]]}

import asyncio
import types
import pytest
from types import SimpleNamespace

import pr_agent.tools.pr_code_suggestions as mod
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class FakeLogger:
    def __init__(self):
        self.calls = []

    def info(self, msg, artifact=None):
        self.calls.append(("info", msg, artifact))

    def debug(self, msg, artifact=None):
        self.calls.append(("debug", msg, artifact))

    def warning(self, msg, artifact=None):
        self.calls.append(("warning", msg, None))

    def error(self, msg, artifact=None):
        self.calls.append(("error", msg, artifact))


@pytest.mark.asyncio
async def test_decouple_hunks_sequential_with_scores_and_errors(monkeypatch):
    # Setup fake settings: decouple_hunks True, no parallel calls, threshold 2
    settings = SimpleNamespace(
        pr_code_suggestions=SimpleNamespace(
            decouple_hunks=True,
            max_number_of_calls=5,
            parallel_calls=False,
            suggestions_score_threshold=2,
        )
    )
    monkeypatch.setattr(mod, "get_settings", lambda: settings)

    # Fake get_pr_multi_diffs returns one patch (decoupled)
    monkeypatch.setattr(mod, "get_pr_multi_diffs", lambda gp, th, model, max_calls, add_line_numbers: ["patch1"])

    # Fake logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Create instance without calling __init__
    inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
    inst.git_provider = "gp"
    inst.token_handler = "th"

    # remove_line_numbers should be called on the decoupled patches list
    inst.remove_line_numbers = lambda lst: ["patch1_no_lines"]

    # _get_prediction returns one dict with three suggestions:
    # - one with score 3 (kept)
    # - one with score 1 (removed because threshold is 2)
    # - one with invalid score string to trigger exception and error logging
    async def fake_get_prediction(self, model, patches_diff, patches_diff_no_line_numbers):
        return {
            "code_suggestions": [
                {"id": "keep_me", "score": "3"},
                {"id": "remove_me", "score": "1"},
                {"id": "bad_score", "score": "not_an_int"},
            ]
        }

    # Bind async method to instance
    inst._get_prediction = types.MethodType(fake_get_prediction, inst)

    # Call the method under test
    data = await inst.prepare_prediction_main("model-x")

    # Assert that only the high-score suggestion remains
    assert data is not None
    assert "code_suggestions" in data
    ids = [s.get("id") for s in data["code_suggestions"]]
    assert ids == ["keep_me"]

    # Check that a removal info and an error were logged
    info_logged = any(call[0] == "info" and "Removing suggestions" in str(call[1]) for call in fake_logger.calls)
    error_logged = any(call[0] == "error" and "Error getting PR diff for suggestion" in str(call[1]) for call in fake_logger.calls)
    assert info_logged, f"Expected removal info logged, got: {fake_logger.calls}"
    assert error_logged, f"Expected error logged for bad score, got: {fake_logger.calls}"

    # Also verify instance.data was set to the same result
    assert inst.data is data


@pytest.mark.asyncio
async def test_non_decouple_hunks_fallback_to_empty_and_warning(monkeypatch):
    # Setup fake settings: decouple_hunks False, doesn't matter parallel_calls
    settings = SimpleNamespace(
        pr_code_suggestions=SimpleNamespace(
            decouple_hunks=False,
            max_number_of_calls=3,
            parallel_calls=False,
            suggestions_score_threshold=1,
        )
    )
    monkeypatch.setattr(mod, "get_settings", lambda: settings)

    # Prepare recorder for get_pr_multi_diffs calls
    calls = []

    def fake_get_pr_multi_diffs(gp, th, model, max_calls, add_line_numbers):
        calls.append({"add_line_numbers": add_line_numbers, "max_calls": max_calls})
        # For add_line_numbers=False return a non-empty placeholder list (initial no-line list)
        # For add_line_numbers=True (fallback) return empty to force empty patches_diff_list
        return ["no_lines"] if not add_line_numbers else []

    monkeypatch.setattr(mod, "get_pr_multi_diffs", fake_get_pr_multi_diffs)

    # Fake logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Create instance and set async convert_to_decoupled_with_line_numbers to return empty list
    inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
    inst.git_provider = "gp"
    inst.token_handler = "th"

    async def fake_convert(self, no_line_list, model):
        return []  # force fallback and then fallback returns empty too

    inst.convert_to_decoupled_with_line_numbers = types.MethodType(fake_convert, inst)

    # Call method
    data = await inst.prepare_prediction_main("m")

    # Assert fallback was attempted and returned None data because patches list empty
    assert any(call["add_line_numbers"] is False for call in calls), "Expected initial call without line numbers"
    assert any(call["add_line_numbers"] is True for call in calls), "Expected fallback call with line numbers"
    assert data is None
    # A warning should have been logged about empty PR diff list
    assert any(c[0] == "warning" and "Empty PR diff list" in c[1] for c in fake_logger.calls)


@pytest.mark.asyncio
async def test_predictions_without_code_suggestions_are_skipped(monkeypatch):
    # Setup settings: decouple_hunks True, sequential
    settings = SimpleNamespace(
        pr_code_suggestions=SimpleNamespace(
            decouple_hunks=True,
            max_number_of_calls=2,
            parallel_calls=False,
            suggestions_score_threshold=1,
        )
    )
    monkeypatch.setattr(mod, "get_settings", lambda: settings)

    # get_pr_multi_diffs returns one patch
    monkeypatch.setattr(mod, "get_pr_multi_diffs", lambda gp, th, model, max_calls, add_line_numbers: ["p"])

    # Fake logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Create instance and wire remove_line_numbers and _get_prediction returning dict w/o 'code_suggestions'
    inst = PRCodeSuggestions.__new__(PRCodeSuggestions)
    inst.git_provider = None
    inst.token_handler = None
    inst.remove_line_numbers = lambda lst: ["p_no_lines"]

    async def fake_pred(self, model, pd, pd_no):
        return {"some_other_key": 123}

    inst._get_prediction = types.MethodType(fake_pred, inst)

    data = await inst.prepare_prediction_main("m")

    # Expect data to be present with empty code_suggestions list
    assert data == {"code_suggestions": []}
    assert inst.data == data
    # Ensure no errors or removals logged
    assert not any(c[0] == "error" for c in fake_logger.calls)
    # Debug/info for PR diff should be logged (info at least)
    assert any(c[0] in ("info", "debug") for c in fake_logger.calls)
