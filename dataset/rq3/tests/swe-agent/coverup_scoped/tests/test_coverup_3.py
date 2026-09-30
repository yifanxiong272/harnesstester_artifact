# file: sweagent/agent/reviewer.py:242-289
# asked: {"lines": [244, 245, 246, 249, 250, 251, 253, 254, 255, 256, 257, 258, 262, 263, 265, 266, 267, 272, 273, 274, 276, 277, 278, 279, 283, 284, 285, 286, 287, 288, 289], "branches": [[249, 250], [249, 253], [261, 265], [261, 266], [286, 287], [286, 289]]}
# gained: {"lines": [244, 245, 246, 249, 250, 251, 253, 254, 255, 256, 257, 258, 262, 263, 265, 266, 267, 272, 273, 274, 276, 277, 278, 279, 283, 284, 285, 286, 287, 288, 289], "branches": [[249, 250], [249, 253], [261, 265], [261, 266], [286, 287], [286, 289]]}

import pytest
from types import SimpleNamespace

import sweagent.agent.reviewer as reviewer


class DummyModel:
    def __init__(self, response_message=""):
        self._response_message = response_message

    def query(self, messages):
        # Emulate the model query returning a dict with "message"
        return {"message": self._response_message}


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.debugs = []
        self.errors = []

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class DummySubmission:
    def __init__(self, submission_value, to_format_dict_return=None):
        self.info = {"submission": submission_value}
        if to_format_dict_return is None:
            to_format_dict_return = {"content": submission_value}
        self._to_format = to_format_dict_return

    def to_format_dict(self):
        return self._to_format


def make_config(model_name="dummy", max_len_submission=0, submission_template="{{content}}",
                instance_template="{{problem_statement}}: {{submissions}}", system_template="SYS"):
    return SimpleNamespace(
        model=model_name,
        max_len_submission=max_len_submission,
        submission_template=submission_template,
        instance_template=instance_template,
        system_template=system_template,
    )


def setup_preselector(monkeypatch, model_response="", logger=None, config=None):
    # Replace get_model and get_logger in the reviewer module
    dummy_model = DummyModel(response_message=model_response)
    monkeypatch.setattr(reviewer, "get_model", lambda *args, **kwargs: dummy_model)
    if logger is None:
        logger = DummyLogger()
    monkeypatch.setattr(reviewer, "get_logger", lambda *args, **kwargs: logger)
    if config is None:
        config = make_config()
    pre = reviewer.Preselector(config)
    return pre, dummy_model, logger


def test_interpret_empty_and_numbers_and_exception(monkeypatch):
    pre, _, logger = setup_preselector(monkeypatch)

    # 1) Empty response -> warning and empty list
    res = pre.interpret("")
    assert res == []
    assert any("No response from preselector" in w for w in logger.warnings)

    # 2) Valid numbers in last line -> returns list of ints
    resp_with_nums = "some text\nchoose 3 and 45"
    res2 = pre.interpret(resp_with_nums)
    assert res2 == [3, 45]

    # 3) Force re.findall to raise to trigger except branch and logger.error
    def raise_findall(pattern, string):
        raise RuntimeError("boom")

    monkeypatch.setattr(reviewer.re, "findall", raise_findall)
    res3 = pre.interpret("last line 123")
    assert res3 == []
    assert any("Error interpreting response" in e for e in logger.errors)


def test_format_submission_invalid_and_valid(monkeypatch):
    # Case A: submission is None -> invalid
    config = make_config(max_len_submission=10, submission_template="{{content}}")
    pre, _, logger = setup_preselector(monkeypatch, config=config)

    sub_none = DummySubmission(None)
    out = pre.format_submission("prob", sub_none)
    assert out == "Solution invalid."

    # Case B: submission too long -> invalid
    long_text = "x" * 50
    sub_long = DummySubmission(long_text)
    config2 = make_config(max_len_submission=10, submission_template="{{content}}")
    # Recreate Preselector with small max length
    monkeypatch.setattr(reviewer, "get_model", lambda *args, **kwargs: DummyModel(""))
    pre2 = reviewer.Preselector(config2)
    out2 = pre2.format_submission("prob", sub_long)
    assert out2 == "Solution invalid."

    # Case C: valid submission -> rendered template
    good_sub = DummySubmission("ok", {"content": "FORMATTED_OK"})
    config3 = make_config(max_len_submission=100, submission_template="{{content}}")
    monkeypatch.setattr(reviewer, "get_model", lambda *args, **kwargs: DummyModel(""))
    pre3 = reviewer.Preselector(config3)
    out3 = pre3.format_submission("prob", good_sub)
    assert out3 == "FORMATTED_OK"


def test_build_messages_and_choose_with_indices(monkeypatch):
    # Setup config and preselector with a model that returns indices "1 2"
    config = make_config(
        max_len_submission=100,
        submission_template="SUB: {{content}}",
        instance_template="PS: {{problem_statement}} | {{submissions}}",
        system_template="SYSTEM-TEMPLATE",
    )
    logger = DummyLogger()
    monkeypatch.setattr(reviewer, "get_model", lambda *args, **kwargs: DummyModel("I choose 1 2"))
    monkeypatch.setattr(reviewer, "get_logger", lambda *args, **kwargs: logger)
    pre = reviewer.Preselector(config)

    subs = [
        DummySubmission("a", {"content": "A"}),
        DummySubmission("b", {"content": "B"}),
        DummySubmission("c", {"content": "C"}),
    ]

    messages = pre.build_messages("ProblemX", subs)
    # messages should have system and user entries
    assert isinstance(messages, list) and len(messages) == 2
    assert messages[0]["role"] == "system" and messages[0]["content"] == config.system_template
    assert messages[1]["role"] == "user"
    assert "ProblemX" in messages[1]["content"]
    # debug log should have been written
    assert any("MODEL INPUT (user)" in d for d in logger.debugs)

    # Now test choose uses model response and interpret to select indices
    out = pre.choose("ProblemX", subs)
    # chosen_idx should reflect numbers in response "1 2" -> [1, 2]
    assert hasattr(out, "chosen_idx")
    assert out.chosen_idx == [1, 2]
    assert out.response == "I choose 1 2"
    # messages returned by choose should be same as those built
    assert out.messages == messages


def test_choose_no_indices_uses_all(monkeypatch):
    # Model returns a message with no digits; interpret will return []
    config = make_config(
        max_len_submission=100,
        submission_template="{{content}}",
        instance_template="PS: {{problem_statement}} | {{submissions}}",
        system_template="SYS",
    )
    logger = DummyLogger()
    monkeypatch.setattr(reviewer, "get_model", lambda *args, **kwargs: DummyModel("no numbers here"))
    monkeypatch.setattr(reviewer, "get_logger", lambda *args, **kwargs: logger)
    pre = reviewer.Preselector(config)

    subs = [DummySubmission("one"), DummySubmission("two"), DummySubmission("three")]

    out = pre.choose("P", subs)
    # interpret returns [], so choose should warn and select all indices [0,1,2]
    assert out.chosen_idx == [0, 1, 2]
    assert any("No indices found in response" in w for w in logger.warnings)
    assert out.response == "no numbers here"
    # messages should be present and include system and user entries
    assert isinstance(out.messages, list) and len(out.messages) == 2
    assert out.messages[0]["role"] == "system"
    assert out.messages[1]["role"] == "user"
