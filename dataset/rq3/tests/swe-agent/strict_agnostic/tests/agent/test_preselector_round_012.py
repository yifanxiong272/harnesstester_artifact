import types
import builtins
import pytest

import sweagent.agent.reviewer as reviewer


class DummyConfig:
    def __init__(self, *, model="dummy", submission_template="{{submission}}", instance_template="INST: {{problem_statement}} | {{submissions}}", system_template="SYS", max_len_submission=10):
        self.model = model
        self.submission_template = submission_template
        self.instance_template = instance_template
        self.system_template = system_template
        self.max_len_submission = max_len_submission


class FakeModel:
    def __init__(self, response_message):
        # response_message will be returned as the model's message
        self._response_message = response_message

    def query(self, messages):
        # deterministic reply structure matching code expectation
        return {"message": self._response_message}


class DummySubmission:
    def __init__(self, info_value, to_dict_return=None):
        # info is used by format_submission
        self.info = {"submission": info_value}
        self._to_dict_return = to_dict_return or {"submission": info_value}

    def to_format_dict(self, suffix: str = ""):
        # signature might include optional suffix in real code; keep compatible
        return dict(self._to_dict_return)


def test_interpret_empty_response_round_012():
    """interpret should return [] and not raise when given an empty response"""
    cfg = DummyConfig()

    # Ensure Preselector uses a fake model (not called in this test, but avoid real get_model)
    monkey_model = FakeModel("")
    # monkeypatch the module-level get_model to return our fake model
    reviewer.get_model = lambda *a, **k: monkey_model

    p = reviewer.Preselector(cfg)

    # explicit empty string - should take the branch 'if not response' -> []
    out = p.interpret("")
    assert out == [], "Empty response should lead to empty indices"


def test_interpret_parse_error_round_012(monkeypatch):
    """If re.findall raises, interpret should catch and return []"""
    cfg = DummyConfig()
    reviewer.get_model = lambda *a, **k: FakeModel("")
    p = reviewer.Preselector(cfg)

    # Make re.findall raise an exception to hit the except branch
    def raise_findall(_pattern, _string):
        raise RuntimeError("forced")

    monkeypatch.setattr(reviewer.re, "findall", raise_findall)

    # A normal non-empty response that would normally parse digits, but our findall raises
    out = p.interpret("Line with 123")
    assert out == [], "On parse exception interpret should return empty list"


def test_format_submission_invalid_none_and_too_long_round_012():
    """format_submission should return 'Solution invalid.' for None or too-long submissions"""
    cfg = DummyConfig(max_len_submission=5)
    reviewer.get_model = lambda *a, **k: FakeModel("")
    p = reviewer.Preselector(cfg)

    # Case 1: submission info has None
    s_none = DummySubmission(None)
    res_none = p.format_submission("prob", s_none)
    assert res_none == "Solution invalid.", "None submission should be invalid"

    # Case 2: submission too long
    s_long = DummySubmission("x" * 20)
    res_long = p.format_submission("prob", s_long)
    assert res_long == "Solution invalid.", "Too long submission should be invalid"


def test_format_submission_valid_round_012():
    """format_submission should render template when valid"""
    cfg = DummyConfig(submission_template="Submitted: {{submission}}", max_len_submission=100)
    reviewer.get_model = lambda *a, **k: FakeModel("")
    p = reviewer.Preselector(cfg)

    # Provide a to_format_dict that produces the key used by the template
    s = DummySubmission("ok", to_dict_return={"submission": "RENDERED"})
    out = p.format_submission("prob", s)
    assert out.strip() == "Submitted: RENDERED"


def test_build_messages_and_choose_with_indices_round_012():
    """choose should parse indices from model response and return them in PreselectorOutput"""
    cfg = DummyConfig()

    # Model returns digits in the message which interpret should parse
    fake = FakeModel("Chosen indices: 2, 3")
    reviewer.get_model = lambda *a, **k: fake

    p = reviewer.Preselector(cfg)

    # Create two dummy submissions; their content is irrelevant for parsing indices
    inputs = [DummySubmission("a"), DummySubmission("b")]

    out = p.choose("prob", inputs)

    # verify structure and parsed indices
    assert hasattr(out, "chosen_idx") and hasattr(out, "response") and hasattr(out, "messages")
    assert out.response == "Chosen indices: 2, 3"
    # interpret should extract [2, 3]
    assert out.chosen_idx == [2, 3]
    # messages should be a list of two dicts with roles system and user
    assert isinstance(out.messages, list) and len(out.messages) == 2
    assert out.messages[0]["role"] == "system"
    assert out.messages[1]["role"] == "user"
    assert cfg.system_template in out.messages[0]["content"] or out.messages[0]["content"] == cfg.system_template


def test_choose_fallback_indices_round_012():
    """If interpret yields no indices, choose should fallback to using all indices"""
    cfg = DummyConfig()

    # Model returns an empty message such that interpret returns []
    fake = FakeModel("")
    reviewer.get_model = lambda *a, **k: fake

    p = reviewer.Preselector(cfg)

    inputs = [DummySubmission("x"), DummySubmission("y")]
    out = p.choose("prob", inputs)

    # When no indices are found, it should fallback to all indices [0, 1]
    assert out.chosen_idx == [0, 1]
    assert out.response == ""
    assert isinstance(out.messages, list) and len(out.messages) == 2
