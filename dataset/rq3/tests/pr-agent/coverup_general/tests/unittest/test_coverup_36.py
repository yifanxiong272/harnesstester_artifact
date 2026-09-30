# file: pr_agent/tools/pr_code_suggestions.py:422-474
# asked: {"lines": [441, 442, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 459, 460, 467, 468, 469, 470, 472, 473, 474], "branches": [[425, 0], [431, 439], [440, 441], [441, 442], [441, 444], [466, 467], [469, 470], [469, 472]]}
# gained: {"lines": [441, 442, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 459, 460, 467, 468, 469, 470, 472], "branches": [[425, 0], [431, 439], [440, 441], [441, 442], [441, 444], [466, 467], [469, 470], [469, 472]]}

import types
import pytest

from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions


class DummyLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []
        self.debug_calls = []

    def info(self, msg, **kwargs):
        self.info_calls.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.error_calls.append((msg, kwargs))

    def debug(self, msg, **kwargs):
        self.debug_calls.append((msg, kwargs))


class RaiseInfoLogger(DummyLogger):
    def info(self, msg, **kwargs):
        raise ValueError("logger info failed")


def make_settings(publish_output=True, commitable=True):
    return types.SimpleNamespace(
        config=types.SimpleNamespace(publish_output=publish_output),
        pr_code_suggestions=types.SimpleNamespace(commitable_code_suggestions=commitable),
    )


def make_prs_instance():
    # Create instance without calling __init__
    prs = object.__new__(PRCodeSuggestions)
    # Provide a simple validator method as used by analyze_self_reflection_response
    prs.validate_one_liner_suggestion_not_repeating_code = types.MethodType(lambda self, s: s, prs)
    return prs


@pytest.mark.asyncio
async def test_exit_on_feedback_length_mismatch(monkeypatch):
    """
    Cover branch where code_suggestions_feedback exists but length doesn't match => function exits early.
    """
    # Arrange
    data = {"code_suggestions": [{"label": "A"}]}
    # Patch the module-level load_yaml used by the function under test
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: {"code_suggestions": []})
    # Patch module-level get_settings and get_logger
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: make_settings(publish_output=False))
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: dummy_logger)

    prs = make_prs_instance()

    # Act
    await prs.analyze_self_reflection_response(data, "irrelevant")

    # Assert - because lengths mismatched, no score or other keys added
    assert "score" not in data["code_suggestions"][0]
    assert dummy_logger.info_calls == [] and dummy_logger.error_calls == []


@pytest.mark.asyncio
async def test_relevant_lines_negative_and_publish_logging(monkeypatch):
    """
    Cover block where 'relevant_lines_start' not in suggestion, relevant lines negative sets score=0,
    and publish_output True leads to logging with score -1 and label normalization.
    """
    # Arrange
    suggestion = {
        "label": "My<br>Label ",
        # no 'relevant_lines_start' to force the branch
        "existing_code": "x = 1",
        "improved_code": "x = 2",
    }
    data = {"code_suggestions": [suggestion]}
    # feedback with negative relevant lines
    feedback = {
        "code_suggestions": [
            {
                "suggestion_score": 5,
                "why": "some reason",
                "relevant_lines_start": -1,
                "relevant_lines_end": -2,
            }
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: feedback)
    # Settings: publish_output True
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: make_settings(publish_output=True, commitable=True))
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: dummy_logger)

    prs = make_prs_instance()

    # Act
    await prs.analyze_self_reflection_response(data, "irrelevant")

    # Assert
    s = data["code_suggestions"][0]
    # relevant lines were set
    assert s["relevant_lines_start"] == -1
    assert s["relevant_lines_end"] == -2
    # score overridden to 0 because relevant lines negative
    assert s["score"] == 0
    # logging should have been called and score normalized to -1 (because falsy 0)
    assert len(dummy_logger.info_calls) == 1
    msg, kwargs = dummy_logger.info_calls[0]
    assert msg.startswith("PR-Agent suggestions statistics")
    stats = kwargs.get("statistics")
    assert stats == {"score": -1, "label": "my label"}


@pytest.mark.asyncio
async def test_inner_logging_exception_is_caught(monkeypatch):
    """
    Cover the inner logging exception path (lines 451-452) by having get_logger.info raise.
    """
    # Arrange
    suggestion = {
        "label": "Label",
        # include relevant_lines_start so code doesn't change score
        "relevant_lines_start": 1,
        "relevant_lines_end": 2,
        "existing_code": "a",
        "improved_code": "b",
    }
    data = {"code_suggestions": [suggestion]}
    feedback = {
        "code_suggestions": [
            {"suggestion_score": 3, "why": "ok"},
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: feedback)
    # Settings: publish_output True to trigger logging
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: make_settings(publish_output=True))
    # Logger whose info raises
    bad_logger = RaiseInfoLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: bad_logger)

    prs = make_prs_instance()

    # Act
    await prs.analyze_self_reflection_response(data, "irrelevant")

    # Assert - info should have raised and was caught, so error was logged
    assert len(bad_logger.info_calls) == 0
    assert len(bad_logger.error_calls) >= 1
    # suggestion score preserved / set to int(3)
    assert data["code_suggestions"][0]["score"] == 3


@pytest.mark.asyncio
async def test_missing_feedback_score_sets_defaults_and_commitable_true(monkeypatch):
    """
    Trigger outer exception when feedback missing 'suggestion_score' to hit lines 455-460.
    Also exercise the branch where commitable_code_suggestions True so improved_code is cleared.
    """
    # Arrange
    suggestion = {
        "label": "L",
        "existing_code": "same",
        "improved_code": "same",
    }
    data = {"code_suggestions": [suggestion]}
    # feedback missing 'suggestion_score' to cause KeyError when accessed
    feedback = {
        "code_suggestions": [
            {"why": "no score provided"},
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: feedback)
    # Settings: publish_output False (logging not important here), commitable True
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: make_settings(publish_output=False, commitable=True))
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: dummy_logger)

    prs = make_prs_instance()

    # Act
    await prs.analyze_self_reflection_response(data, "irrelevant")

    # Assert outer except set defaults
    s = data["code_suggestions"][0]
    assert s["score"] == 7
    assert s["score_why"] == ""
    # since existing == improved and commitable True, improved_code cleared
    assert s["improved_code"] == ""


@pytest.mark.asyncio
async def test_missing_feedback_score_and_commitable_false(monkeypatch):
    """
    Similar to previous test but with commitable False to ensure existing_code is cleared.
    """
    # Arrange
    suggestion = {
        "label": "L2",
        "existing_code": "same2",
        "improved_code": "same2",
    }
    data = {"code_suggestions": [suggestion]}
    feedback = {
        "code_suggestions": [
            {"why": "no score again"},
        ]
    }
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.load_yaml", lambda x: feedback)
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_settings", lambda: make_settings(publish_output=False, commitable=False))
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.tools.pr_code_suggestions.get_logger", lambda: dummy_logger)

    prs = make_prs_instance()

    # Act
    await prs.analyze_self_reflection_response(data, "irrelevant")

    # Assert defaults set and existing_code cleared
    s = data["code_suggestions"][0]
    assert s["score"] == 7
    assert s["score_why"] == ""
    assert s["existing_code"] == ""
