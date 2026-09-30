# file: sweagent/agent/reviewer.py:242-289
# asked: {"lines": [244, 245, 246, 249, 250, 251, 253, 254, 255, 256, 257, 258, 262, 263, 265, 266, 267, 272, 273, 274, 276, 277, 278, 279, 283, 284, 285, 286, 287, 288, 289], "branches": [[249, 250], [249, 253], [261, 265], [261, 266], [286, 287], [286, 289]]}
# gained: {"lines": [244, 245, 246, 249, 250, 251, 253, 254, 255, 256, 257, 258, 262, 263, 265, 266, 267, 272, 273, 274, 276, 277, 278, 279, 283, 284, 285, 286, 287, 288, 289], "branches": [[249, 250], [249, 253], [261, 265], [261, 266], [286, 287], [286, 289]]}

import importlib
from types import SimpleNamespace

import pytest


def make_fake_logger():
    class FakeLogger:
        def __init__(self):
            self.warnings = []
            self.errors = []
            self.debugs = []

        def warning(self, msg):
            self.warnings.append(msg)

        def error(self, msg):
            self.errors.append(msg)

        def debug(self, msg):
            self.debugs.append(msg)

    return FakeLogger()


class FakeModel:
    def __init__(self, response_message):
        self._response = response_message
        self.queries = []

    def query(self, messages):
        self.queries.append(messages)
        return {"message": self._response}


def make_config(**kwargs):
    defaults = {
        "model": "dummy-model",
        "submission_template": "submission: {{submission}}",
        "instance_template": "Problem: {{problem_statement}}\nSubmissions:\n{% for s in submissions %}- {{s}}\n{% endfor %}",
        "system_template": "SYSTEM",
        "max_len_submission": 5,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.parametrize("response, expected_indices", [
    ("", []),                    # empty response -> interpret returns [] and warning
    ("Some text\nselected 2 4", [2, 4]),  # numeric extraction from last line
])
def test_interpret_empty_and_numeric(monkeypatch, response, expected_indices):
    # Import module under test and patch dependencies before instantiation
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    fake_logger = make_fake_logger()
    # Patch get_model to a simple fake model and get_logger to our fake logger factory
    monkeypatch.setattr(reviewer, "get_model", lambda model, tc: FakeModel("irrelevant"))
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: fake_logger)

    cfg = make_config()
    # Instantiate Preselector (will call patched get_model and get_logger)
    selector = reviewer.Preselector(cfg)

    # Test interpret behavior
    res = selector.interpret(response)
    assert res == expected_indices

    if response == "":
        # Should have logged a warning for empty response
        assert any("No response from preselector" in w for w in fake_logger.warnings)
    else:
        # No warning expected for non-empty response
        assert not any("No response from preselector" in w for w in fake_logger.warnings)


def test_interpret_exception_path(monkeypatch):
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    fake_logger = make_fake_logger()
    monkeypatch.setattr(reviewer, "get_model", lambda model, tc: FakeModel("irrelevant"))
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: fake_logger)

    cfg = make_config()
    selector = reviewer.Preselector(cfg)

    # Monkeypatch the re.findall used inside interpret to raise
    def raising_findall(pattern, string):
        raise RuntimeError("boom")

    monkeypatch.setattr(reviewer.re, "findall", raising_findall)

    result = selector.interpret("line\nno-digits")
    # On exception, interpret should log an error and return empty list
    assert result == []
    assert any("Error interpreting response" in e for e in fake_logger.errors)


def test_format_submission_build_messages_and_choose(monkeypatch):
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    # Prepare fake logger and model; we'll swap model on the selector later for different responses
    fake_logger = make_fake_logger()
    monkeypatch.setattr(reviewer, "get_logger", lambda name, emoji=None: fake_logger)

    # Patch get_model used during init to create a placeholder model (we'll replace it)
    monkeypatch.setattr(reviewer, "get_model", lambda model, tc: FakeModel("unused"))

    cfg = make_config(
        submission_template="Submitted: {{submission}}",
        instance_template="Problem: {{problem_statement}}\nSubmissions:\n{% for s in submissions %}- {{s}}\n{% endfor %}",
        system_template="SYS-TEMPLATE",
        max_len_submission=5,
    )
    selector = reviewer.Preselector(cfg)

    # Create fake ReviewSubmission-like objects
    class RS:
        def __init__(self, submission_value):
            self.info = {"submission": submission_value}

        def to_format_dict(self):
            # Template expects 'submission' variable
            return {"submission": self.info.get("submission")}

    # Case A: submission is None -> invalid
    rs_none = RS(None)
    out_none = selector.format_submission("prob", rs_none)
    assert out_none == "Solution invalid."

    # Case B: submission too long -> invalid (len > max_len_submission > 0)
    long_text = "x" * (cfg.max_len_submission + 1)
    rs_long = RS(long_text)
    out_long = selector.format_submission("prob", rs_long)
    assert out_long == "Solution invalid."

    # Case C: valid submission -> rendered template
    rs_valid = RS("ok")
    out_valid = selector.format_submission("prob", rs_valid)
    assert out_valid == "Submitted: ok"

    # Build messages using two submissions (one valid, one invalid) and verify contents
    inputs = [rs_valid, rs_none]
    messages = selector.build_messages("Solve X", inputs)
    # Expect two messages: system and user
    assert isinstance(messages, list) and len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == cfg.system_template
    assert messages[1]["role"] == "user"
    # The rendered user content should include the problem statement and the formatted submissions
    assert "Solve X" in messages[1]["content"]
    assert "- Submitted: ok" in messages[1]["content"]
    assert "- Solution invalid." in messages[1]["content"]

    # Now test choose:
    # 1) when model returns indices in message
    selector.model = FakeModel("1 0")  # choose index 1 and 0 (order preserved by interpret)
    chosen = selector.choose("PS", inputs)
    # chosen should be a PreselectorOutput with chosen_idx matching interpret result
    assert hasattr(chosen, "chosen_idx")
    assert chosen.chosen_idx == [1, 0]
    assert chosen.response == "1 0"
    # messages built inside choose should reflect the problem statement passed to choose ("PS")
    assert isinstance(chosen.messages, list) and len(chosen.messages) == 2
    assert chosen.messages[0]["role"] == "system" and chosen.messages[0]["content"] == cfg.system_template
    assert "Problem: PS" in chosen.messages[1]["content"]
    assert "- Submitted: ok" in chosen.messages[1]["content"]
    assert "- Solution invalid." in chosen.messages[1]["content"]

    # 2) when model returns empty message -> interpret returns [] -> uses all indices
    selector.model = FakeModel("")  # empty message triggers fallback
    chosen2 = selector.choose("PS", inputs)
    assert chosen2.chosen_idx == list(range(len(inputs)))
    assert any("No indices found in response" in w for w in fake_logger.warnings)
    assert chosen2.response == ""
    # messages should again be built and have same two entries and reflect "PS"
    assert isinstance(chosen2.messages, list) and len(chosen2.messages) == 2
    assert "Problem: PS" in chosen2.messages[1]["content"]
