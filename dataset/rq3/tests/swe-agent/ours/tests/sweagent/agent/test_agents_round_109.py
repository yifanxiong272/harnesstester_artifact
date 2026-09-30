from types import SimpleNamespace
import pytest
from sweagent.agent import agents


class FakeLogger:
    def __init__(self):
        self.called = []

    def warning(self, msg):
        # store messages for assertions
        self.called.append(msg)


def _call_warnings_with(obj):
    # Access the raw function behind possible pydantic decorator
    raw = getattr(agents.TemplateConfig, "warnings")
    func = getattr(raw, "__wrapped__", raw)
    # Call the underlying function with the fake instance as self
    return func(obj)


def test_warnings_logs_when_put_demos_and_demo_template_round_109(monkeypatch):
    fake_logger = FakeLogger()

    def fake_get_logger(name, emoji=None):
        return fake_logger

    # Patch the logger factory used inside the warnings method
    monkeypatch.setattr(agents, "get_logger", fake_get_logger)

    obj = SimpleNamespace(
        put_demos_in_history=True,
        demonstration_template="some demo",
        system_template="",
        instance_template=None,
    )

    # Call warnings and assert it returns the same self (per signature)
    ret = _call_warnings_with(obj)
    assert ret is obj

    # Two warnings are expected: one for demonstration_template being ignored,
    # and one for missing system/instance templates.
    assert len(fake_logger.called) >= 2
    assert any(
        "demonstration_template is ignored when put_demos_in_history is True" in m
        for m in fake_logger.called
    )
    assert any(
        "system_template/instance_template is not set" in m
        for m in fake_logger.called
    )


def test_warnings_no_logs_when_all_templates_present_round_109(monkeypatch):
    fake_logger = FakeLogger()

    def fake_get_logger(name, emoji=None):
        return fake_logger

    monkeypatch.setattr(agents, "get_logger", fake_get_logger)

    obj = SimpleNamespace(
        put_demos_in_history=False,
        demonstration_template="some demo",
        system_template="sys",
        instance_template="inst",
    )

    ret = _call_warnings_with(obj)
    assert ret is obj

    # No warnings should have been emitted when templates are present and
    # put_demos_in_history is False
    assert fake_logger.called == []
