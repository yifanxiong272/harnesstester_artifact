# file: sweagent/agent/agents.py:127-138
# asked: {"lines": [131], "branches": [[130, 131]]}
# gained: {"lines": [131], "branches": [[130, 131]]}

import pytest

from sweagent.agent.agents import TemplateConfig


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg: str):
        # store the message for assertions
        self.warnings.append(msg)


def make_get_logger_return(logger):
    def _get_logger(*args, **kwargs):
        return logger
    return _get_logger


def test_both_warnings_triggered(monkeypatch):
    """
    Trigger both warnings:
    - put_demos_in_history True and demonstration_template not None -> first warning (line 131)
    - system_template/instance_template empty -> second warning
    """
    logger = DummyLogger()
    # Patch the get_logger used inside the agents module (it was imported there at module import time)
    monkeypatch.setattr("sweagent.agent.agents.get_logger", make_get_logger_return(logger), raising=True)

    cfg = TemplateConfig(
        put_demos_in_history=True,
        demonstration_template="some demo",
        # leave system_template and instance_template as defaults ('') to trigger second warning
    )

    # model validator returns self, ensure object created
    assert isinstance(cfg, TemplateConfig)
    # two warnings should have been emitted
    assert len(logger.warnings) == 2
    assert "demonstration_template is ignored when put_demos_in_history is True" in logger.warnings[0]
    assert "system_template/instance_template is not set" in logger.warnings[1]


def test_only_demonstration_warning_when_templates_set(monkeypatch):
    """
    When put_demos_in_history True and demonstration_template set, but both templates are non-empty,
    only the demonstration_template warning should be emitted.
    """
    logger = DummyLogger()
    monkeypatch.setattr("sweagent.agent.agents.get_logger", make_get_logger_return(logger), raising=True)

    cfg = TemplateConfig(
        put_demos_in_history=True,
        demonstration_template="demo content",
        system_template="non-empty system",
        instance_template="non-empty instance",
    )

    assert isinstance(cfg, TemplateConfig)
    # only the demonstration_template warning should be present
    assert len(logger.warnings) == 1
    assert "demonstration_template is ignored when put_demos_in_history is True" in logger.warnings[0]


def test_only_system_instance_warning_when_no_demo(monkeypatch):
    """
    When demonstration_template is None but system/instance templates are empty,
    only the system/instance warning should be emitted.
    """
    logger = DummyLogger()
    monkeypatch.setattr("sweagent.agent.agents.get_logger", make_get_logger_return(logger), raising=True)

    cfg = TemplateConfig(
        put_demos_in_history=True,
        demonstration_template=None,
        # system_template and instance_template default to empty -> trigger second warning
    )

    assert isinstance(cfg, TemplateConfig)
    assert len(logger.warnings) == 1
    assert "system_template/instance_template is not set" in logger.warnings[0]
