import builtins
from types import SimpleNamespace
import pytest

import sweagent.agent.reviewer as reviewer


class FakeLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.debugs = []

    def warning(self, msg):
        self.warnings.append(str(msg))

    def error(self, msg):
        self.errors.append(str(msg))

    def debug(self, msg):
        self.debugs.append(str(msg))


class FakeModel:
    def __init__(self, return_message):
        self._return = return_message
        self.queries = []

    def query(self, messages):
        # record messages for inspection and return a deterministic response
        self.queries.append(messages)
        return {"message": self._return}


class StubSubmission:
    def __init__(self, info, fmt_dict=None):
        self.info = info
        # default to return the submission text under key 'text' if no dict provided
        self._fmt = fmt_dict if fmt_dict is not None else {"text": info.get("submission", "")}

    def to_format_dict(self):
        return dict(self._fmt)


def make_config(**kwargs):
    defaults = {
        "model": "fake-model",
        "max_len_submission": 1000,
        "submission_template": "{{text}}",
        "instance_template": "Problem: {{problem_statement}}\nSubmissions:\n{% for s in submissions %}- {{s}}\n{% endfor %}",
        "system_template": "SYSTEM_TEMPLATE",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_choose_with_empty_model_response_uses_all_indices_round_010(monkeypatch):
    # Arrange: patch get_model and get_logger to deterministic fakes
    fake_logger = FakeLogger()
    fake_model = FakeModel("")

    monkeypatch.setattr(reviewer, "get_model", lambda model, toolconfig: fake_model)
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: fake_logger)

    cfg = make_config()
    pre = reviewer.Preselector(cfg)

    submissions = [StubSubmission({"submission": "alpha"}), StubSubmission({"submission": "beta"})]

    # Act
    out = pre.choose("the problem", submissions)

    # Assert: when model returns empty message, interpret returns [], and choose falls back to all indices
    assert out.chosen_idx == [0, 1]
    assert out.response == ""

    # messages should contain system and user entries with rendered instance message
    assert isinstance(out.messages, list)
    assert out.messages[0]["role"] == "system"
    assert out.messages[0]["content"] == cfg.system_template
    assert out.messages[1]["role"] == "user"
    assert "Problem: the problem" in out.messages[1]["content"]
    # ensure the user content mentions the two submissions produced by format_submission
    assert "alpha" in out.messages[1]["content"]
    assert "beta" in out.messages[1]["content"]

    # Two warnings: one from interpret (no response) and one from choose (no indices found)
    assert any("No response from preselector" in w for w in fake_logger.warnings)
    assert any("No indices found in response" in w for w in fake_logger.warnings)


def test_format_submission_valid_and_invalid_branches_round_010(monkeypatch):
    # Patch logger and model so Preselector constructs successfully but we only test format_submission
    monkeypatch.setattr(reviewer, "get_model", lambda model, toolconfig: FakeModel("irrelevant"))
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: FakeLogger())

    # Case A: submission missing -> should return "Solution invalid."
    cfg = make_config(max_len_submission=10, submission_template="{{text}}")
    pre = reviewer.Preselector(cfg)

    missing = StubSubmission({"submission": None}, fmt_dict={"text": "ignored"})
    assert pre.format_submission("p", missing) == "Solution invalid."

    # Case B: submission too long -> should return "Solution invalid."
    cfg2 = make_config(max_len_submission=2, submission_template="{{text}}")
    pre2 = reviewer.Preselector(cfg2)
    longsub = StubSubmission({"submission": "longtext"}, fmt_dict={"text": "longtext"})
    assert pre2.format_submission("p", longsub) == "Solution invalid."

    # Case C: valid submission and template rendering path
    cfg3 = make_config(max_len_submission=100, submission_template="Rendered: {{value}}")
    pre3 = reviewer.Preselector(cfg3)
    good = StubSubmission({"submission": "ok"}, fmt_dict={"value": "YES"})
    assert pre3.format_submission("p", good) == "Rendered: YES"


def test_interpret_handles_regex_exception_and_logs_error_round_010(monkeypatch):
    # Arrange a Preselector with a fake logger
    fake_logger = FakeLogger()
    monkeypatch.setattr(reviewer, "get_model", lambda model, toolconfig: FakeModel("irrelevant"))
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: fake_logger)

    pre = reviewer.Preselector(make_config())

    # Monkeypatch the findall used inside the reviewer module to raise an exception
    def raising_findall(pattern, text):
        raise RuntimeError("boom")

    monkeypatch.setattr(reviewer.re, "findall", raising_findall)

    # Act
    res = pre.interpret("some text 123")

    # Assert: should return empty list and log an error mentioning the exception
    assert res == []
    assert any("Error interpreting response" in e or "boom" in e for e in fake_logger.errors)
