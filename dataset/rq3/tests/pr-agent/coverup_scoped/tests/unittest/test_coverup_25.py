# file: pr_agent/servers/github_app.py:253-309
# asked: {"lines": [273, 274, 275, 279, 280, 281, 282, 283, 284, 289, 290, 291, 292, 293, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308], "branches": [[272, 273], [273, 274], [273, 278], [278, 279], [280, 281], [280, 282], [282, 283], [282, 287], [288, 289], [290, 291], [290, 296], [298, 299], [299, 300], [299, 303], [303, 304], [303, 309]]}
# gained: {"lines": [273, 274, 275, 279, 280, 281, 282, 283, 284, 289, 290, 291, 292, 293, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308], "branches": [[272, 273], [273, 274], [278, 279], [280, 281], [282, 283], [288, 289], [290, 291], [298, 299], [299, 300], [299, 303], [303, 304]]}

import pytest

import pr_agent.servers.github_app as gh_app


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


def test_ignore_pr_author(monkeypatch):
    logger = DummyLogger()
    # make get_settings return an author-ignore list
    monkeypatch.setattr(gh_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_AUTHORS": [r"baduser"]})
    monkeypatch.setattr(gh_app, "get_logger", lambda: logger)

    body = {
        "sender": {"login": "baduser"},
        "pull_request": {},  # minimal
        "repository": {"full_name": "some/repo"},
    }

    result = gh_app.should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR from user 'baduser'" in m for m in logger.infos)


def test_ignore_pr_title_nonlist_and_conversion(monkeypatch):
    logger = DummyLogger()
    # return a non-list title pattern to exercise the conversion branch
    monkeypatch.setattr(gh_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_TITLE": r"skip me"})
    monkeypatch.setattr(gh_app, "get_logger", lambda: logger)

    body = {
        "pull_request": {"title": "please skip me"},
        "sender": {"login": "somebody"},
        "repository": {"full_name": "some/repo"},
    }

    # Pattern 'skip me' should match "please skip me"
    result = gh_app.should_process_pr_logic(body)
    assert result is False
    assert any("Ignoring PR with title" in m for m in logger.infos)


def test_ignore_pr_labels(monkeypatch):
    logger = DummyLogger()
    monkeypatch.setattr(gh_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_LABELS": ["wip"]})
    monkeypatch.setattr(gh_app, "get_logger", lambda: logger)

    body = {
        "pull_request": {"labels": [{"name": "wip"}, {"name": "other"}]},
        "sender": {"login": "somebody"},
        "repository": {"full_name": "some/repo"},
    }

    result = gh_app.should_process_pr_logic(body)
    assert result is False
    # Should mention the labels joined by comma and space
    assert any("wip, other" in m for m in logger.infos)


def test_ignore_pr_source_and_target_branch_matching(monkeypatch):
    logger = DummyLogger()
    # First: source branch matches -> should short-circuit on source
    monkeypatch.setattr(
        gh_app,
        "get_settings",
        lambda: {
            "CONFIG.IGNORE_PR_SOURCE_BRANCHES": [r"skip-source"],
            "CONFIG.IGNORE_PR_TARGET_BRANCHES": [r"skip-target"],
        },
    )
    monkeypatch.setattr(gh_app, "get_logger", lambda: logger)

    body_source = {
        "pull_request": {
            "head": {"ref": "feature/skip-source-123"},
            "base": {"ref": "develop"},
            "title": "",
            "labels": [],
        },
        "sender": {"login": "someone"},
        "repository": {"full_name": "some/repo"},
    }

    res1 = gh_app.should_process_pr_logic(body_source)
    assert res1 is False
    assert any("source branch" in m for m in logger.infos)

    # Clear logger and test target branch matching (when source does not match)
    logger.infos.clear()
    body_target = {
        "pull_request": {
            "head": {"ref": "feature/good"},
            "base": {"ref": "refs/heads/skip-target"},
            "title": "",
            "labels": [],
        },
        "sender": {"login": "someone"},
        "repository": {"full_name": "some/repo"},
    }

    res2 = gh_app.should_process_pr_logic(body_target)
    assert res2 is False
    assert any("target branch" in m for m in logger.infos)


def test_exception_in_get_settings_is_logged_and_function_returns_true(monkeypatch):
    logger = DummyLogger()

    def raising_get_settings():
        raise RuntimeError("boom")

    monkeypatch.setattr(gh_app, "get_settings", raising_get_settings)
    monkeypatch.setattr(gh_app, "get_logger", lambda: logger)

    body = {
        "pull_request": {"title": "anything"},
        "sender": {"login": "someone"},
        "repository": {"full_name": "some/repo"},
    }

    # Should catch the exception, log an error, and still return True (as per implementation)
    result = gh_app.should_process_pr_logic(body)
    assert result is True
    assert any("Failed 'should_process_pr_logic'" in e for e in logger.errors)
