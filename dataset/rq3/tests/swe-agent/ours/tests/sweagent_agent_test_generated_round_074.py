import types
import builtins
import pytest

import sweagent.agent.reviewer as reviewer


class DummyConfig:
    def __init__(self, max_len_submission: int, submission_template: str):
        self.max_len_submission = max_len_submission
        self.submission_template = submission_template


class DummySubmission:
    def __init__(self, info: dict, fmt: dict = None):
        self.info = info
        # to_format_dict should return a mapping used by template render
        self._fmt = fmt or {"code": "print(42)"}

    def to_format_dict(self):
        return dict(self._fmt)


class FakeTemplate:
    """A tiny deterministic stand-in for jinja2.Template.

    It captures the template text passed on construction and returns a
    deterministic string from render() using the provided kwargs so tests
    can assert the exact output and inspect that the right kwargs were
    forwarded.
    """

    last_instance = None

    def __init__(self, text: str):
        self.text = text
        FakeTemplate.last_instance = self

    def render(self, **kwargs):
        # Deterministic representation of kwargs: sort keys for stability.
        items = tuple((k, kwargs[k]) for k in sorted(kwargs.keys()))
        return f"FAKE_RENDER:{self.text}|{items}"


def make_self(config: DummyConfig):
    # Create a minimal 'self' object expected by Chooser.format_submission
    return types.SimpleNamespace(config=config)


def test_format_submission_none_round_074(monkeypatch):
    """When submission.info['submission'] is None we return the invalid message."""
    # Patch Template to avoid invoking real jinja2 and to ensure determinism
    monkeypatch.setattr(reviewer, "Template", FakeTemplate)

    cfg = DummyConfig(max_len_submission=10, submission_template="tpl")
    self_obj = make_self(cfg)

    sub = DummySubmission(info={"submission": None}, fmt={"x": "y"})

    res = reviewer.Chooser.format_submission(self_obj, "problem", sub)

    assert res == "Solution invalid.", "Expected invalid message when submission key is None"
    # Ensure Template was not constructed (since invalid branch returns early)
    assert FakeTemplate.last_instance is None


def test_format_submission_length_exceeds_round_074(monkeypatch):
    """When the submission text length exceeds config.max_len_submission (>0) we return invalid."""
    monkeypatch.setattr(reviewer, "Template", FakeTemplate)

    # max_len_submission set to 3 and submission length 5 -> triggers invalid branch
    cfg = DummyConfig(max_len_submission=3, submission_template="tpl-long")
    self_obj = make_self(cfg)

    sub = DummySubmission(info={"submission": "ABCDE"}, fmt={"code": "x"})

    res = reviewer.Chooser.format_submission(self_obj, "problem", sub)

    assert res == "Solution invalid."
    # Template should not have been used
    assert FakeTemplate.last_instance is None


def test_format_submission_valid_render_round_074(monkeypatch):
    """When submission is present and within max_len_submission, Template.render is invoked with
    the values from submission.to_format_dict and its output returned unchanged.
    """
    # Patch the Template symbol used by the module to our FakeTemplate
    monkeypatch.setattr(reviewer, "Template", FakeTemplate)

    cfg = DummyConfig(max_len_submission=10, submission_template="my-template-{{code}}")
    self_obj = make_self(cfg)

    payload = {"code": "print('ok')", "author": "tester"}
    sub = DummySubmission(info={"submission": "OK"}, fmt=payload)

    res = reviewer.Chooser.format_submission(self_obj, "irrelevant-problem", sub)

    # The fake template returns a deterministic string including the template text and the kwargs
    assert res.startswith("FAKE_RENDER:"), "Expected the fake template render result to be returned"
    # Confirm fake template was constructed with the exact submission_template from the config
    assert FakeTemplate.last_instance is not None
    assert FakeTemplate.last_instance.text == cfg.submission_template
    # Confirm that the kwargs passed to render matched the dict returned by to_format_dict()
    expected_items = tuple((k, payload[k]) for k in sorted(payload.keys()))
    assert res == f"FAKE_RENDER:{cfg.submission_template}|{expected_items}"
