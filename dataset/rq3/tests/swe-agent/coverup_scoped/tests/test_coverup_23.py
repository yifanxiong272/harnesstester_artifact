# file: sweagent/agent/reviewer.py:382-398
# asked: {"lines": [383, 384, 385, 386, 387, 389, 390, 391, 392, 394, 395, 396, 397], "branches": []}
# gained: {"lines": [383, 384, 385, 386, 387, 389, 390, 391, 392, 394, 395, 396, 397], "branches": []}

import types
import pytest
from sweagent.agent import reviewer as reviewer_mod


class _DummyProblemStatement:
    def __init__(self, ps_text: str, extra: dict):
        self._ps_text = ps_text
        self._extra = extra

    def get_problem_statement(self) -> str:
        return self._ps_text

    def get_extra_fields(self) -> dict:
        return dict(self._extra)


class _DummySubmission:
    def __init__(self, format_dict: dict, trajectory):
        self._format = dict(format_dict)
        self.trajectory = trajectory

    def to_format_dict(self) -> dict:
        return dict(self._format)


class _CaptureLogger:
    def __init__(self):
        self.calls = []

    def debug(self, msg: str):
        # store messages for assertions
        self.calls.append(msg)


def _make_reviewer_with_config(system_template: str, instance_template: str, traj_formatter_callable):
    """
    Construct a Reviewer instance without running __init__ to avoid
    needing full ReviewerConfig/TetureFormatter setup. Assigns only
    the attributes used by format_messages.
    """
    rev = reviewer_mod.Reviewer.__new__(reviewer_mod.Reviewer)
    # lightweight config object with required attributes
    rev._config = types.SimpleNamespace(
        system_template=system_template,
        instance_template=instance_template,
    )
    # traj formatter with a format_trajectory method
    rev._traj_formatter = types.SimpleNamespace(format_trajectory=traj_formatter_callable)
    # logger that captures debug calls
    rev.logger = _CaptureLogger()
    return rev


def test_format_messages_renders_templates_and_returns_messages():
    # Arrange
    system_tmpl = "SYSTEM_TEMPLATE_v1"
    # Use placeholders for problem_statement, extra field 'difficulty',
    # a submission field named 'score', and the traj variable.
    instance_tmpl = "PS: {{ problem_statement }} | DIFF: {{ difficulty }} | SCORE: {{ score }} | TRAJ: {{ traj }}"
    traj_callable = lambda traj: f"TRAJ_FMT[{traj}]"
    reviewer = _make_reviewer_with_config(system_tmpl, instance_tmpl, traj_callable)

    instance = _DummyProblemStatement("Solve X", {"difficulty": "hard"})
    submission = _DummySubmission({"score": 0.95}, trajectory="traj-data-123")

    # Act
    messages = reviewer_mod.Reviewer.format_messages(reviewer, instance, submission)

    # Assert: structure and content
    assert isinstance(messages, list)
    assert len(messages) == 2

    system_msg = messages[0]
    user_msg = messages[1]

    assert system_msg == {"role": "system", "content": system_tmpl}

    # user message should contain rendered values
    expected_user_content = "PS: Solve X | DIFF: hard | SCORE: 0.95 | TRAJ: TRAJ_FMT[traj-data-123]"
    assert user_msg["role"] == "user"
    assert user_msg["content"] == expected_user_content

    # logger debug should have been called twice (system and user)
    assert len(reviewer.logger.calls) == 2
    assert reviewer.logger.calls[0] == f"MODEL INPUT (system)\n{system_tmpl}"
    assert reviewer.logger.calls[1] == f"MODEL INPUT (user)\n{expected_user_content}"


def test_format_messages_merges_extra_and_submission_fields_without_collision():
    # This test ensures extra fields and submission fields are both available
    # and that rendering works when keys do not collide.
    system_tmpl = "SYS"
    instance_tmpl = "EXTRA_ONLY: {{ extra_only }} | SUB_ONLY: {{ sub_only }} | TRAJ: {{ traj }}"

    traj_callable = lambda traj: f"F[{traj}]"
    reviewer = _make_reviewer_with_config(system_tmpl, instance_tmpl, traj_callable)

    # extra contains 'extra_only'
    instance = _DummyProblemStatement("ignored", {"extra_only": "E"})
    # submission contains 'sub_only' (no collision)
    submission = _DummySubmission({"sub_only": "S"}, trajectory="xyz")

    messages = reviewer_mod.Reviewer.format_messages(reviewer, instance, submission)

    user_content = messages[1]["content"]
    assert "EXTRA_ONLY: E" in user_content
    assert "SUB_ONLY: S" in user_content
    assert "TRAJ: F[xyz]" in user_content

    # Ensure system message still correct and logger captured entries
    assert messages[0]["content"] == system_tmpl
    assert reviewer.logger.calls[0] == f"MODEL INPUT (system)\n{system_tmpl}"
