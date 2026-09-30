# file: pr_agent/git_providers/azuredevops_provider.py:437-461
# asked: {"lines": [438, 439, 440, 441, 442, 443, 444, 445, 446, 448, 449, 450, 453, 454, 455, 457, 458, 459, 460, 461], "branches": [[439, 440], [439, 461], [453, 439], [453, 454], [458, 459], [458, 460]]}
# gained: {"lines": [438, 439, 440, 441, 442, 443, 444, 445, 446, 448, 449, 450, 453, 454, 455, 457, 458, 459, 460, 461], "branches": [[439, 440], [439, 461], [453, 454], [458, 459]]}

import types
import pytest

from pr_agent.git_providers import azuredevops_provider as azmod
from pr_agent.git_providers.azuredevops_provider import AzureDevopsProvider


class DummyConfig:
    def __init__(self, verbosity_level):
        self.verbosity_level = verbosity_level


class DummySettings:
    def __init__(self, verbosity_level):
        self.config = DummyConfig(verbosity_level)


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def make_comment():
    return {
        "body": "suggestion body",
        "path": "some/file.py",
        "absolute_position": 10,
        "position": 2,
    }


def test_publish_inline_comments_success_verbose(monkeypatch):
    # Prepare dummy settings and logger with verbosity >= 2
    dummy_settings = DummySettings(verbosity_level=2)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(azmod, "get_settings", lambda: dummy_settings)
    monkeypatch.setattr(azmod, "get_logger", lambda: dummy_logger)

    # Create provider instance without running __init__
    provider = object.__new__(AzureDevopsProvider)
    # set required attributes
    provider.pr_num = 123
    called = []

    # Define publish_comment to capture inputs and return a dummy Comment-like object
    def fake_publish_comment(pr_comment, is_temporary=False, thread_context=None):
        called.append({"pr_comment": pr_comment, "is_temporary": is_temporary, "thread_context": thread_context})
        return {"id": 1}

    provider.publish_comment = fake_publish_comment

    comments = [make_comment()]

    result = provider.publish_inline_comments(comments)

    assert result is True
    assert len(called) == 1
    call = called[0]
    assert call["pr_comment"] == "suggestion body"
    tc = call["thread_context"]
    assert tc["filePath"] == "some/file.py"
    assert tc["rightFileStart"]["line"] == 10
    assert tc["rightFileStart"]["offset"] == 2
    assert tc["rightFileEnd"]["line"] == 10
    assert tc["rightFileEnd"]["offset"] == 2

    # Logger info should have been called once with pr number and path
    assert len(dummy_logger.infos) == 1
    assert f"{provider.pr_num}" in dummy_logger.infos[0]
    assert "some/file.py" in dummy_logger.infos[0]
    # No errors
    assert dummy_logger.errors == []


def test_publish_inline_comments_exception_handling_verbose(monkeypatch):
    # Prepare dummy settings and logger with verbosity >= 2
    dummy_settings = DummySettings(verbosity_level=2)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(azmod, "get_settings", lambda: dummy_settings)
    monkeypatch.setattr(azmod, "get_logger", lambda: dummy_logger)

    provider = object.__new__(AzureDevopsProvider)
    provider.pr_num = 999

    # publish_comment will raise to trigger the except branch
    def raising_publish_comment(pr_comment, is_temporary=False, thread_context=None):
        raise ValueError("boom")

    provider.publish_comment = raising_publish_comment

    comments = [make_comment(), make_comment()]

    result = provider.publish_inline_comments(comments)

    # Should be False because publish_comment raised for at least one comment
    assert result is False

    # Logger should have recorded an error for each failing comment (verbosity >=2)
    assert len(dummy_logger.errors) == 2
    for err in dummy_logger.errors:
        assert "Failed to publish code suggestion" in err or "boom" in err or "Failed" in err
        assert "boom" in err or "boom" in err  # ensure original message shown
