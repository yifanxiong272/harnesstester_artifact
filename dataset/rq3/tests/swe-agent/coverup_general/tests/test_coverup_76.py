# file: sweagent/agent/reviewer.py:318-327
# asked: {"lines": [319, 320, 321, 323, 324, 325, 326], "branches": []}
# gained: {"lines": [319, 320, 321, 323, 324, 325, 326], "branches": []}

import pytest
from types import SimpleNamespace

import sweagent.agent.reviewer as reviewer_module
from sweagent.agent.reviewer import Chooser


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        self.messages.append(msg)


def make_chooser(instance_template=None, system_template=None, monkeypatch=None):
    # Ensure external dependencies are stubbed before creating Chooser
    if monkeypatch is None:
        raise RuntimeError("make_chooser requires monkeypatch fixture to stub external dependencies")

    # Fake get_model to avoid heavy initialization
    def fake_get_model(model_name, tool_config):
        return object()

    # Fake get_logger to return our DummyLogger
    def fake_get_logger(name, *args, **kwargs):
        return DummyLogger()

    monkeypatch.setattr(reviewer_module, "get_model", fake_get_model)
    monkeypatch.setattr(reviewer_module, "get_logger", fake_get_logger)

    cfg = SimpleNamespace(
        model="dummy-model",
        instance_template=instance_template
        or "Problem: {{problem_statement}}; Subs: {% for s in submissions %}{{s}}|{% endfor %}",
        system_template=system_template or "SYS_TEMPLATE",
    )
    return Chooser(cfg)


def test_build_messages_renders_and_logs(monkeypatch):
    chooser = make_chooser(monkeypatch=monkeypatch)

    # Record calls to format_submission
    calls = []

    def fake_format(problem_statement, submission):
        calls.append((problem_statement, submission))
        return f"formatted-{getattr(submission, 'id', submission)}"

    # Monkeypatch the instance method on the chooser instance
    monkeypatch.setattr(chooser, "format_submission", fake_format, raising=False)

    subs = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    problem_statement = "Add two numbers"

    messages = chooser.build_messages(problem_statement, subs)

    # Assert format_submission was called for each submission with correct problem statement
    assert len(calls) == 2
    assert calls[0] == (problem_statement, subs[0])
    assert calls[1] == (problem_statement, subs[1])

    # Build expected rendered user content
    expected_user_content = "Problem: Add two numbers; Subs: formatted-1|formatted-2|"

    # Assert logger.debug was called once and contains the rendered message after the header
    assert isinstance(chooser.logger, DummyLogger)
    assert len(chooser.logger.messages) == 1
    assert chooser.logger.messages[0].startswith("MODEL INPUT (user)\n")
    assert chooser.logger.messages[0].endswith(expected_user_content)

    # Assert returned messages structure
    assert messages == [
        {"role": "system", "content": chooser.config.system_template},
        {"role": "user", "content": expected_user_content},
    ]


def test_build_messages_with_empty_submissions(monkeypatch):
    chooser = make_chooser(
        instance_template="PS: {{problem_statement}}; SUBS=[{% for s in submissions %}{{s}}, {% endfor %}]",
        system_template="SYSTEM_OK",
        monkeypatch=monkeypatch,
    )

    calls = []

    def fake_format(problem_statement, submission):
        calls.append((problem_statement, submission))
        return "should-not-be-used"

    monkeypatch.setattr(chooser, "format_submission", fake_format, raising=False)

    messages = chooser.build_messages("No submissions here", [])

    # format_submission should not have been called
    assert calls == []

    expected_user = "PS: No submissions here; SUBS=[]"

    # Logger should have been called with the rendered empty submissions
    assert isinstance(chooser.logger, DummyLogger)
    assert len(chooser.logger.messages) == 1
    assert chooser.logger.messages[0].endswith(expected_user)

    # Returned messages must include system and the rendered (empty) user content
    assert messages == [
        {"role": "system", "content": "SYSTEM_OK"},
        {"role": "user", "content": expected_user},
    ]
