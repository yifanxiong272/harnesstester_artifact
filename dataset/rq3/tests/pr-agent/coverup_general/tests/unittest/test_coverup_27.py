# file: pr_agent/servers/github_app.py:253-309
# asked: {"lines": [273, 274, 275, 279, 280, 281, 282, 283, 284, 289, 290, 291, 292, 293, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308], "branches": [[272, 273], [273, 274], [273, 278], [278, 279], [280, 281], [280, 282], [282, 283], [282, 287], [288, 289], [290, 291], [290, 296], [298, 299], [299, 300], [299, 303], [303, 304], [303, 309]]}
# gained: {"lines": [273, 274, 275, 279, 280, 281, 282, 283, 284, 289, 290, 291, 292, 293, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308], "branches": [[272, 273], [273, 274], [278, 279], [280, 281], [280, 282], [282, 283], [288, 289], [290, 291], [298, 299], [299, 300], [299, 303], [303, 304]]}

import re
import pytest

from pr_agent.servers import github_app


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg, *args, **kwargs):
        self.infos.append(msg)

    def error(self, msg, *args, **kwargs):
        self.errors.append(msg)


def make_get_settings(mapping):
    def _get_settings():
        return mapping
    return _get_settings


def test_ignore_pr_user(monkeypatch):
    logger = DummyLogger()
    # Patch the functions used inside should_process_pr_logic in the module namespace
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({"CONFIG.IGNORE_PR_AUTHORS": [r"^baduser$"]}),
    )

    body = {
        "sender": {"login": "baduser"},
        "pull_request": {},
        "repository": {"full_name": "some/repo"},
    }

    result = github_app.should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR from user 'baduser' due to 'config.ignore_pr_authors' setting" in m for m in logger.infos)


def test_ignore_pr_title_non_list_and_list(monkeypatch):
    logger = DummyLogger()
    # Will test non-list string first
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    # Title configured as string (not list) should be coerced into list
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({"CONFIG.IGNORE_PR_TITLE": r"\[WIP\]"}),
    )

    body = {
        "pull_request": {"title": "[WIP] Work in progress"},
        "sender": {"login": "someone"},
        "repository": {"full_name": "org/repo"},
    }

    result = github_app.should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with title '[WIP] Work in progress' due to config.ignore_pr_title setting" in m for m in logger.infos)

    # Now test when IGNORE_PR_TITLE is already a list
    logger = DummyLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({"CONFIG.IGNORE_PR_TITLE": [r"^Ignore me$"]}),
    )
    body["pull_request"]["title"] = "Ignore me"
    result = github_app.should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with title 'Ignore me' due to config.ignore_pr_title setting" in m for m in logger.infos)


def test_ignore_pr_labels(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({"CONFIG.IGNORE_PR_LABELS": ["wontfix", "skip-ci"]}),
    )

    body = {
        "pull_request": {
            "labels": [{"name": "wontfix"}, {"name": "other"}],
        },
        "sender": {"login": "someone"},
        "repository": {"full_name": "org/repo"},
    }

    result = github_app.should_process_pr_logic(body)
    assert result is False
    # Should mention the labels as a joined string
    assert any("Ignoring PR with labels 'wontfix, other' due to config.ignore_pr_labels settings" in m for m in logger.infos)


def test_ignore_pr_source_and_target_branches(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)

    # Case 1: source branch matches ignore pattern
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({
            "CONFIG.IGNORE_PR_SOURCE_BRANCHES": [r"^dependabot/.*$"],
            "CONFIG.IGNORE_PR_TARGET_BRANCHES": [],
        }),
    )

    body_source = {
        "pull_request": {
            "head": {"ref": "dependabot/npm_and_yarn"},
            "base": {"ref": "main"},
        },
        "sender": {"login": "user"},
        "repository": {"full_name": "org/repo"},
    }

    result = github_app.should_process_pr_logic(body_source)
    assert result is False
    assert any("Ignoring PR with source branch 'dependabot/npm_and_yarn' due to config.ignore_pr_source_branches settings" in m for m in logger.infos)

    # Case 2: target branch matches ignore pattern (source doesn't)
    logger = DummyLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(
        github_app,
        "get_settings",
        make_get_settings({
            "CONFIG.IGNORE_PR_SOURCE_BRANCHES": [r"^no-match$"],
            "CONFIG.IGNORE_PR_TARGET_BRANCHES": [r"^release-.*$"],
        }),
    )

    body_target = {
        "pull_request": {
            "head": {"ref": "feature/xyz"},
            "base": {"ref": "release-1.2"},
        },
        "sender": {"login": "user"},
        "repository": {"full_name": "org/repo"},
    }

    result = github_app.should_process_pr_logic(body_target)
    assert result is False
    assert any("Ignoring PR with target branch 'release-1.2' due to config.ignore_pr_target_branches settings" in m for m in logger.infos)


def test_exception_path_logs_error_and_returns_true(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)

    def raising_get_settings():
        raise ValueError("boom")

    monkeypatch.setattr(github_app, "get_settings", raising_get_settings)

    body = {
        "pull_request": {"title": "something"},
        "sender": {"login": "user"},
        "repository": {"full_name": "org/repo"},
    }

    # When get_settings raises, should_process_pr_logic should catch and log error and still return True
    result = github_app.should_process_pr_logic(body)
    assert result is True
    assert any("Failed 'should_process_pr_logic': boom" in m for m in logger.errors)
