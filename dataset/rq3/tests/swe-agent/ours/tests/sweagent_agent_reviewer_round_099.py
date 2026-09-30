import types
import pytest

import sweagent.agent.reviewer as reviewer


class DummyModel:
    """A harmless stand-in for the real model returned by get_model."""
    def __init__(self):
        self.name = "dummy"


class LoggerMock:
    def __init__(self):
        self.calls = []

    def debug(self, msg):
        # Preserve the exact string passed so tests can assert on it.
        self.calls.append(msg)


def test_build_messages_renders_template_and_logs_round_099(monkeypatch):
    # Arrange: patch get_model to avoid any external model creation
    monkeypatch.setattr(reviewer, "get_model", lambda *a, **k: DummyModel())

    # Replace get_logger so we can capture debug output deterministically
    logger = LoggerMock()
    monkeypatch.setattr(reviewer, "get_logger", lambda *a, **k: logger)

    # Build a minimal config object with the attributes the Chooser expects
    config = types.SimpleNamespace(
        model="dummy-model",
        instance_template=(
            "Problem: {{ problem_statement }}\n"
            "Submissions: {% for s in submissions %}{{ s }}|{% endfor %}"
        ),
        system_template="SYSTEM-TEMPLATE",
    )

    chooser = reviewer.Chooser(config)

    # Spy: record calls to format_submission and return predictable string values
    calls = []

    def _fmt(self, problem_statement, submission):
        calls.append((problem_statement, submission))
        return f"formatted:{submission}"

    chooser.format_submission = types.MethodType(_fmt, chooser)

    # Act: call build_messages with two simple submissions
    problem = "MyProblemStatement"
    submissions = ["sub1", "sub2"]
    messages = chooser.build_messages(problem, submissions)

    # Assert: format_submission called for each submission with the right problem_statement
    assert calls == [(problem, "sub1"), (problem, "sub2")]

    # The instance message should be the template rendered with our formatted submissions
    expected_instance = (
        "Problem: MyProblemStatement\nSubmissions: formatted:sub1|formatted:sub2|"
    )

    # logger.debug should have been called once with the exact debug string
    assert len(logger.calls) == 1
    assert logger.calls[0] == f"MODEL INPUT (user)\n{expected_instance}"

    # The returned messages should include the system template and the rendered user content
    assert messages == [
        {"role": "system", "content": config.system_template},
        {"role": "user", "content": expected_instance},
    ]


def test_build_messages_with_empty_submissions_round_099(monkeypatch):
    # Ensure behavior when input list is empty — still renders and logs correctly
    monkeypatch.setattr(reviewer, "get_model", lambda *a, **k: DummyModel())
    logger = LoggerMock()
    monkeypatch.setattr(reviewer, "get_logger", lambda *a, **k: logger)

    config = types.SimpleNamespace(
        model="dummy-model",
        instance_template=(
            "Problem: {{ problem_statement }}\n"
            "Submissions: {% for s in submissions %}{{ s }}|{% endfor %}"
        ),
        system_template="SYS",
    )

    chooser = reviewer.Chooser(config)

    # format_submission should not be called at all for empty input
    def _fmt(self, problem_statement, submission):
        raise AssertionError("format_submission should not be called for empty input")

    chooser.format_submission = types.MethodType(_fmt, chooser)

    messages = chooser.build_messages("P", [])

    # Expect empty submissions rendering (no items between markers)
    expected_instance = "Problem: P\nSubmissions: "
    assert logger.calls == [f"MODEL INPUT (user)\n{expected_instance}"]
    assert messages == [{"role": "system", "content": "SYS"}, {"role": "user", "content": expected_instance}]
