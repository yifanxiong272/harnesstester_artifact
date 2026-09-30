# file: pr_agent/tools/pr_code_suggestions.py:422-474
# asked: {"lines": [441, 442, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 459, 460, 467, 468, 469, 470, 472, 473, 474], "branches": [[425, 0], [431, 439], [440, 441], [441, 442], [441, 444], [466, 467], [469, 470], [469, 472]]}
# gained: {"lines": [441, 442, 445, 446, 447, 448, 449, 450, 455, 456, 457, 458, 459, 460, 467, 468, 469, 470, 472], "branches": [[425, 0], [440, 441], [441, 442], [466, 467], [469, 470], [469, 472]]}

import asyncio
from types import SimpleNamespace
import pytest

from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class DummyLogger:
    def __init__(self, raise_on_info=False):
        self.info_calls = []
        self.error_calls = []
        self.debug_calls = []
        self.raise_on_info = raise_on_info

    def info(self, msg, **kwargs):
        if self.raise_on_info:
            raise RuntimeError("info failed")
        self.info_calls.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.error_calls.append((msg, kwargs))

    def debug(self, msg, **kwargs):
        self.debug_calls.append((msg, kwargs))


@pytest.mark.parametrize(
    "response_yaml",
    [
        {},  # no code_suggestions key
        {"code_suggestions": []},  # empty list
    ],
)
def test_no_feedback_exits(monkeypatch, response_yaml):
    """
    Ensure that when no feedback is present (or empty list), the method exits early
    and does not modify suggestions.
    """
    # Prepare data with one suggestion
    suggestion = {
        "label": "Label",
        "existing_code": "a=1",
        "improved_code": "a=2",
    }
    data = {"code_suggestions": [suggestion.copy()]}

    # Monkeypatch load_yaml in the module where it's used
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: response_yaml)

    # Replace get_settings and get_logger in the module under test
    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=False),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: logger)

    # Ensure validate_one_liner_* is identity
    monkeypatch.setattr(
        "pr_agent.tools.pr_code_suggestions.PRCodeSuggestions.validate_one_liner_suggestion_not_repeating_code",
        lambda self, s: s,
    )

    # Create instance without running __init__
    prcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    asyncio.run(prcs.analyze_self_reflection_response(data, "unused"))

    # Since no feedback, suggestion should be unchanged
    assert data["code_suggestions"][0] == suggestion
    # No logger calls should be made
    assert logger.info_calls == []
    assert logger.error_calls == []
    assert logger.debug_calls == []


def test_publish_output_score_falsy_and_info_called(monkeypatch):
    """
    Test path where relevant lines are negative, which forces suggestion['score']=0 (falsy),
    publish_output is True, and logger.info is called with score -1 and processed label.
    """
    # Single suggestion without 'relevant_lines_start' so code will set them from feedback
    suggestion = {
        "label": "Foo<br>Bar",
        "existing_code": "x",
        "improved_code": "y",
    }
    data = {"code_suggestions": [suggestion]}

    # Feedback contains suggestion_score but relevant lines negative -> sets suggestion['score']=0
    response_yaml = {
        "code_suggestions": [
            {
                "suggestion_score": 5,
                "why": "ok",
                "relevant_lines_start": -1,
                "relevant_lines_end": -2,
            }
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: response_yaml)

    # Settings: publish_output True to trigger logging
    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=True),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    # Dummy logger that records info calls
    logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: logger)

    # validate_* returns unchanged
    monkeypatch.setattr(
        "pr_agent.tools.pr_code_suggestions.PRCodeSuggestions.validate_one_liner_suggestion_not_repeating_code",
        lambda self, s: s,
    )

    prcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    asyncio.run(prcs.analyze_self_reflection_response(data, "unused"))

    # After processing, score should have been set to 0 by relevant_lines check
    processed = data["code_suggestions"][0]
    assert processed["score"] == 0
    assert processed["score_why"] == "ok"

    # Logger.info should have been called once with statistics containing score -1 and label processed
    assert len(logger.info_calls) == 1
    msg, kwargs = logger.info_calls[0]
    stats = kwargs.get("statistics")
    assert stats is not None
    assert stats["score"] == -1
    # label was lowercased and '<br>' replaced by space -> "foo bar"
    assert "foo bar" in stats["label"]


def test_publish_output_info_raises_logs_error_and_outer_except_sets_defaults(monkeypatch):
    """
    Test that if logger.info raises, the inner except handles it and logs error.
    Also test outer except: provide feedback missing 'suggestion_score' to trigger KeyError
    in the assignment and ensure suggestion['score'] is set to 7 and score_why to "".
    Also test the branch for existing_code==improved_code and commitable flag handling (True).
    """
    # Suggestion where existing_code == improved_code to trigger that branch
    suggestion = {
        "label": "SomeLabel",
        "existing_code": "same",
        "improved_code": "same",
    }
    data = {"code_suggestions": [suggestion]}

    # Feedback missing 'suggestion_score' to trigger KeyError -> outer except executed
    response_yaml = {"code_suggestions": [{"why": "no score"}]}
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: response_yaml)

    # Settings: publish_output True and commitable True
    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=True),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=True),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    # Logger whose info will raise if called
    logger = DummyLogger(raise_on_info=True)
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: logger)

    # validate_* returns unchanged
    monkeypatch.setattr(
        "pr_agent.tools.pr_code_suggestions.PRCodeSuggestions.validate_one_liner_suggestion_not_repeating_code",
        lambda self, s: s,
    )

    prcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    asyncio.run(prcs.analyze_self_reflection_response(data, "unused"))

    processed = data["code_suggestions"][0]
    # Outer except should set score to 7 and score_why to empty string
    assert processed["score"] == 7
    assert processed["score_why"] == ""

    # Because existing_code == improved_code and commitable_code_suggestions True,
    # improved_code should be cleared
    assert processed["improved_code"] == ""
    # debug was called to note the edit
    assert any("edited improved suggestion" in call[0] for call in logger.debug_calls)


def test_existing_code_improved_code_equality_commitable_false(monkeypatch):
    """
    Test the branch where existing_code == improved_code and commitable_code_suggestions is False,
    which should clear existing_code.
    """
    suggestion = {
        "label": "Lbl",
        "existing_code": "identical",
        "improved_code": "identical",
    }
    data = {"code_suggestions": [suggestion]}

    # Provide valid feedback so no outer except; include positive relevant lines to avoid resetting score
    response_yaml = {
        "code_suggestions": [
            {
                "suggestion_score": 3,
                "why": "fine",
                "relevant_lines_start": 1,
                "relevant_lines_end": 2,
            }
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: response_yaml)

    # Settings: publish_output False so no logger.info calls needed, commitable False to take 'else' path
    settings = SimpleNamespace(
        config=SimpleNamespace(publish_output=False),
        pr_code_suggestions=SimpleNamespace(commitable_code_suggestions=False),
    )
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: settings)

    # Logger to capture debug
    logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: logger)

    # validate_* returns unchanged
    monkeypatch.setattr(
        "pr_agent.tools.pr_code_suggestions.PRCodeSuggestions.validate_one_liner_suggestion_not_repeating_code",
        lambda self, s: s,
    )

    prcs = PRCodeSuggestions.__new__(PRCodeSuggestions)
    asyncio.run(prcs.analyze_self_reflection_response(data, "unused"))

    processed = data["code_suggestions"][0]
    # Score should be set from feedback (3)
    assert processed["score"] == 3
    # Because existing == improved and commitable False, existing_code should be cleared
    assert processed["existing_code"] == ""
    # improved_code should remain unchanged since commitable True branch would clear improved_code,
    # but here commitable is False so existing_code cleared instead
    assert processed["improved_code"] == "identical"
    assert any("edited improved suggestion" in call[0] for call in logger.debug_calls)
