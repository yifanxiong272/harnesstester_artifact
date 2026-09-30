import re
import pytest
import pr_agent.servers.github_app as ga
from pr_agent.servers.github_app import should_process_pr_logic


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg, *args, **kwargs):
        # store formatted message for inspection
        try:
            self.infos.append(str(msg))
        except Exception:
            self.infos.append(repr(msg))

    def error(self, msg, *args, **kwargs):
        try:
            self.errors.append(str(msg))
        except Exception:
            self.errors.append(repr(msg))


def _patch_settings_and_logger(monkeypatch, settings, logger):
    """Helper to patch get_settings and get_logger in the target module."""
    # get_settings should be callable returning the dict
    monkeypatch.setattr(ga, "get_settings", lambda: settings)
    # get_logger should return the logger object
    monkeypatch.setattr(ga, "get_logger", lambda: logger)


def test_ignore_repo_round_053(monkeypatch):
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_REPOSITORIES": [r"^ignored/repo$"]}
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "", "labels": [], "head": {"ref": ""}, "base": {"ref": ""}},
        "repository": {"full_name": "ignored/repo"},
        "sender": {"login": "someuser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    # verify logger captured the ignore reason
    assert any("Ignoring PR from repository" in m for m in logger.infos)
    assert any("ignored/repo" in m for m in logger.infos)


def test_ignore_pr_author_round_053(monkeypatch):
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_PR_AUTHORS": [r"^baduser$"]}
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "ok", "labels": [], "head": {"ref": ""}, "base": {"ref": ""}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "baduser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR from user" in m for m in logger.infos)
    assert any("baduser" in m for m in logger.infos)


def test_ignore_pr_title_conversion_round_053(monkeypatch):
    # CONFIG.IGNORE_PR_TITLE may be a single string; code converts it to a list
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_PR_TITLE": r"^WIP"}
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "WIP: work in progress", "labels": [], "head": {"ref": ""}, "base": {"ref": ""}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "gooduser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with title" in m for m in logger.infos)
    assert any("WIP: work in progress" in m for m in logger.infos)


def test_ignore_labels_round_053(monkeypatch):
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_PR_LABELS": ["skip", "do-not-merge"]}
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "ok", "labels": [{"name": "skip"}, {"name": "other"}], "head": {"ref": ""}, "base": {"ref": ""}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "gooduser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    # ensure the labels string is formed and logged
    assert any("Ignoring PR with labels" in m for m in logger.infos)
    assert any("skip" in m and "other" in m for m in logger.infos)


def test_ignore_source_branch_round_053(monkeypatch):
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_PR_SOURCE_BRANCHES": [r"^feature/.*$"]}
    # no target branch ignores here
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "ok", "labels": [], "head": {"ref": "feature/x"}, "base": {"ref": "dev"}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "gooduser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with source branch" in m for m in logger.infos)
    assert any("feature/x" in m for m in logger.infos)


def test_ignore_target_branch_round_053(monkeypatch):
    logger = DummyLogger()
    settings = {"CONFIG.IGNORE_PR_TARGET_BRANCHES": [r"^main$"]}
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "ok", "labels": [], "head": {"ref": "feature/x"}, "base": {"ref": "main"}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "gooduser"},
    }

    result = should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with target branch" in m for m in logger.infos)
    assert any("main" in m for m in logger.infos)


def test_no_ignore_returns_true_round_053(monkeypatch):
    # when settings do not match anything, we should return True
    logger = DummyLogger()
    settings = {
        "CONFIG.IGNORE_REPOSITORIES": [],
        "CONFIG.IGNORE_PR_AUTHORS": [],
        "CONFIG.IGNORE_PR_TITLE": [],
        "CONFIG.IGNORE_PR_LABELS": [],
        "CONFIG.IGNORE_PR_SOURCE_BRANCHES": [],
        "CONFIG.IGNORE_PR_TARGET_BRANCHES": [],
    }
    _patch_settings_and_logger(monkeypatch, settings, logger)

    body = {
        "pull_request": {"title": "normal", "labels": [{"name": "ok"}], "head": {"ref": "feat/x"}, "base": {"ref": "dev"}},
        "repository": {"full_name": "owner/repo"},
        "sender": {"login": "gooduser"},
    }

    result = should_process_pr_logic(body)
    assert result is True
    # and no error was logged
    assert logger.errors == []
