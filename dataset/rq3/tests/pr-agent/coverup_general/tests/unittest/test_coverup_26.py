# file: pr_agent/servers/bitbucket_server_webhook.py:44-124
# asked: {"lines": [70, 71, 72, 85, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 115, 116, 118, 119, 120, 121, 122, 123, 124], "branches": [[69, 70], [70, 71], [70, 75], [76, 82], [82, 90], [84, 85], [92, 103], [97, 103], [104, 105], [104, 124], [110, 112], [110, 124], [113, 114], [113, 118], [114, 113], [114, 115], [118, 119], [118, 124]]}
# gained: {"lines": [70, 71, 72, 85, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 118, 119, 120, 121, 122, 123], "branches": [[69, 70], [70, 71], [76, 82], [84, 85], [92, 103], [104, 105], [110, 112], [113, 114], [113, 118], [114, 113], [118, 119]]}

import pytest

from types import SimpleNamespace

# Import the function under test
from pr_agent.servers.bitbucket_server_webhook import should_process_pr_logic


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class DummySettings(dict):
    """
    Mimic get_settings() return object:
    - has .get(key, default) like a dict
    - has .config dict with .get(...)
    """
    def __init__(self, mapping=None, config=None):
        mapping = mapping or {}
        super().__init__(mapping)
        self.config = config or {}

    def get(self, key, default=None):
        return super().get(key, default)


class DummyProvider:
    def __init__(self, pr_url=None, changed_files=None, raise_on_get=False):
        self.pr_url = pr_url
        self._changed_files = changed_files or []
        self._raise = raise_on_get

    def get_files(self):
        if self._raise:
            raise RuntimeError("provider failed")
        return self._changed_files


def _make_pr(
    title="Title",
    source="feature/x",
    target="main",
    project_key="",
    repo_slug="",
    author_name="",
    pr_id=None,
):
    pr = {
        "title": title,
        "fromRef": {"displayId": source} if source is not None else {},
        "toRef": {"displayId": target, "repository": {"slug": repo_slug, "project": {"key": project_key}}}
        if (project_key or repo_slug)
        else {"displayId": target},
        "author": {"user": {"name": author_name}} if author_name is not None else {},
    }
    if pr_id is not None:
        pr["id"] = pr_id
    return {"pullRequest": pr}


def test_ignore_repository(monkeypatch):
    """
    Cover lines 70-72: repository full name matches ignore regex and returns False.
    """
    dummy_logger = DummyLogger()
    # Patch the names imported in the module under test
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_logger", lambda: dummy_logger)
    settings = DummySettings({"CONFIG.IGNORE_REPOSITORIES": [r"^KEY/repo$"]}, config={})
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_settings", lambda: settings)

    data = _make_pr(project_key="KEY", repo_slug="repo", author_name="someone", pr_id=1)
    result = should_process_pr_logic(data)
    assert result is False
    # Ensure the expected log message was produced
    assert any("Ignoring PR from repository 'KEY/repo' due to 'config.ignore_repositories' setting" in m for m in dummy_logger.infos)


def test_ignore_pr_user_match(monkeypatch):
    """
    Cover branch where ignore_pr_users present and sender matches -> returns False.
    Ensure repo_full_name is empty so repo-ignore doesn't preempt.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_logger", lambda: dummy_logger)

    settings = DummySettings({"CONFIG.IGNORE_PR_AUTHORS": [r"bob"]}, config={})
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_settings", lambda: settings)

    # No repository info to avoid repo-ignore earlier in the logic
    pr = {
        "pullRequest": {
            "title": "Some title",
            "fromRef": {"displayId": "feature/1"},
            "toRef": {"displayId": "main"},  # no repository -> repo_full_name empty
            "author": {"user": {"name": "bob"}},
            "id": None,
        }
    }

    result = should_process_pr_logic(pr)
    assert result is False
    assert any("Ignoring PR from user 'bob' due to 'config.ignore_pr_authors' setting" in m for m in dummy_logger.infos)


def test_sender_empty_and_title_scalar_converted_and_matched(monkeypatch):
    """
    Cover branch 76->82 (sender empty so user-ignore skipped) and line 85 (ignore title not list => converted).
    Provide a scalar ignore title regex (string) that matches title -> returns False.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_logger", lambda: dummy_logger)

    # ignore users present but sender will be empty -> should be skipped
    settings = DummySettings(
        {
            "CONFIG.IGNORE_PR_AUTHORS": [r"someone"],
            # Provide a scalar (not list) for title ignore to trigger conversion at line 85
            "CONFIG.IGNORE_PR_TITLE": r"WIP",
        },
        config={},
    )
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_settings", lambda: settings)

    # Author present but empty name -> sender becomes ""
    data = _make_pr(title="WIP: work in progress", source=None, target="main", project_key="", repo_slug="", author_name="", pr_id=None)
    result = should_process_pr_logic(data)
    assert result is False
    assert any("Ignoring PR with title 'WIP: work in progress' due to config.ignore_pr_title setting" in m for m in dummy_logger.infos)


def test_allowed_folders_all_files_outside(monkeypatch):
    """
    Cover 103-120: allowed_folders present and provider returns changed files all outside allowed folders -> return False.
    Also ensures flow goes through title-check without matching (82->90).
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_logger", lambda: dummy_logger)

    # Settings: no repo/user/title/source/target ignores, allowed_folders present via .config
    settings = DummySettings(
        {
            "CONFIG.IGNORE_REPOSITORIES": [],
            "CONFIG.IGNORE_PR_AUTHORS": [],
            "CONFIG.IGNORE_PR_TITLE": [],
            "CONFIG.IGNORE_PR_SOURCE_BRANCHES": [],
            "CONFIG.IGNORE_PR_TARGET_BRANCHES": [],
            "BITBUCKET_SERVER.URL": "http://bit",
        },
        config={"allow_only_specific_folders": ["src/allowed/"]},
    )
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_settings", lambda: settings)

    # Monkeypatch the provider class that will be imported inside the function
    monkeypatch.setattr(
        "pr_agent.git_providers.bitbucket_server_provider.BitbucketServerProvider",
        lambda pr_url=None: DummyProvider(pr_url=pr_url, changed_files=["other/file.py", "docs/readme.md"]),
    )

    data = _make_pr(title="Some title", source="feature/x", target="main", project_key="PROJ", repo_slug="myrepo", author_name="dev", pr_id=42)
    result = should_process_pr_logic(data)
    assert result is False
    # ensure the allowed-folders log is present
    assert any("Ignoring PR because all files" in msg and "outside allowed folders" in msg for msg in dummy_logger.infos)


def test_exception_handling_returns_true_and_logs_error(monkeypatch):
    """
    Force get_settings to raise to hit the exception handler (lines 121-124).
    The function should return True and an error should be logged.
    """
    dummy_logger = DummyLogger()
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_logger", lambda: dummy_logger)

    def raise_settings():
        raise RuntimeError("boom")

    # Patch the name imported into the module under test to raise
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_webhook.get_settings", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    data = _make_pr(title="X", source="f", target="t", project_key="K", repo_slug="R", author_name="u", pr_id=1)
    result = should_process_pr_logic(data)
    assert result is True
    # Error log should have been called with message containing Failed 'should_process_pr_logic'
    assert any("Failed 'should_process_pr_logic'" in m for m in dummy_logger.errors)
