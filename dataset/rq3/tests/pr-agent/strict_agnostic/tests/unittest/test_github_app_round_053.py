import pytest

from pr_agent.servers import github_app


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        # keep deterministic representation
        self.infos.append(str(msg))

    def error(self, msg):
        self.errors.append(str(msg))


def _base_body(**overrides):
    # minimal valid PR body scaffold used by tests
    pr = {
        "pull_request": {
            "title": overrides.get("title", ""),
            "labels": overrides.get("labels", []),
            "head": {"ref": overrides.get("source_branch", "")},
            "base": {"ref": overrides.get("target_branch", "")},
        },
        "sender": {"login": overrides.get("sender", None)},
        "repository": {"full_name": overrides.get("repo_full_name", "org/repo")},
    }
    return pr


def test_ignore_pr_user_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    # configure settings to ignore user 'baduser'
    monkeypatch.setattr(github_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_AUTHORS": [r"^baduser$"]})

    body = _base_body(sender="baduser")

    result = github_app.should_process_pr_logic(body)

    assert result is False
    # ensure informative log was emitted
    assert any("Ignoring PR from user 'baduser'" in m for m in logger.infos)


def test_ignore_pr_title_non_list_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    # set a single string (not a list) to trigger the conversion branch
    monkeypatch.setattr(github_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_TITLE": "WIP"})

    body = _base_body(title="WIP: update")

    result = github_app.should_process_pr_logic(body)

    assert result is False
    # the logged message should include the title
    assert any("Ignoring PR with title 'WIP: update'" in m for m in logger.infos)


def test_ignore_pr_labels_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(github_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_LABELS": ["skip-ci"]})

    body = _base_body(labels=[{"name": "skip-ci"}])

    result = github_app.should_process_pr_logic(body)

    assert result is False
    # ensure labels are joined and present in log
    assert any("Ignoring PR with labels 'skip-ci'" in m for m in logger.infos)


def test_ignore_pr_source_branch_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    monkeypatch.setattr(github_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_SOURCE_BRANCHES": [r"dependabot"]})

    body = _base_body(source_branch="dependabot/gh-action")

    # the regex 'dependabot' should match the source branch
    result = github_app.should_process_pr_logic(body)

    assert result is False
    assert any("Ignoring PR with source branch" in m and "dependabot/gh-action" in m for m in logger.infos)


def test_ignore_pr_target_branch_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    # ensure source branch does not match but target does
    monkeypatch.setattr(github_app, "get_settings", lambda: {"CONFIG.IGNORE_PR_TARGET_BRANCHES": [r"stable"]})

    body = _base_body(source_branch="main", target_branch="stable")

    result = github_app.should_process_pr_logic(body)

    assert result is False
    assert any("Ignoring PR with target branch 'stable'" in m for m in logger.infos)


def test_exception_returns_true_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)

    # make get_settings raise to trigger the exception handler
    def raise_settings():
        raise RuntimeError("boom")

    monkeypatch.setattr(github_app, "get_settings", raise_settings)

    body = _base_body()

    # should catch the exception, log an error, and return True
    result = github_app.should_process_pr_logic(body)

    assert result is True
    assert any("Failed 'should_process_pr_logic'" in m for m in logger.errors)


def test_no_ignores_returns_true_round_053(monkeypatch):
    logger = FakeLogger()
    monkeypatch.setattr(github_app, "get_logger", lambda: logger)
    # default settings: nothing to ignore
    monkeypatch.setattr(github_app, "get_settings", lambda: {})

    body = _base_body(title="normal title", labels=[{"name": "ok"}], source_branch="dev", target_branch="main", sender="contributor")

    result = github_app.should_process_pr_logic(body)

    assert result is True
    # no error logs should be present
    assert logger.errors == []
