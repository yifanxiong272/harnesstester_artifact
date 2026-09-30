# file: pr_agent/git_providers/gitea_provider.py:712-739
# asked: {"lines": [718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 737, 738, 739], "branches": [[722, 723], [722, 725], [726, 727], [726, 729], [729, 730], [729, 732], [733, 734], [733, 737]]}
# gained: {"lines": [718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 737, 738, 739], "branches": [[722, 723], [722, 725], [726, 727], [726, 729], [729, 730], [729, 732], [733, 734], [733, 737]]}

import types
import pytest
from pr_agent.git_providers import gitea_provider
from pr_agent.git_providers.gitea_provider import GiteaProvider


class LoggerStub:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def _call_prepare(monkeypatch, self_obj, repo_url):
    logger = LoggerStub()
    monkeypatch.setattr(gitea_provider, "get_logger", lambda: logger)
    result = GiteaProvider._prepare_clone_url_with_token(self_obj, repo_url)
    return result, logger


def test_prepare_clone_url_missing_token(monkeypatch):
    # Missing token should return None and log an error
    self_obj = types.SimpleNamespace()
    self_obj.gitea_access_token = None
    # include a full URL; base_url value must be something (it will be checked after token)
    self_obj.base_url = "https://gitea.example.com"

    result, logger = _call_prepare(monkeypatch, self_obj, "https://gitea.example.com/user/repo.git")

    assert result is None
    assert logger.errors, "Expected an error to be logged when token or base_url missing"
    assert "Either missing auth token or missing base url" in logger.errors[0]


def test_prepare_clone_url_empty_base_after_scheme(monkeypatch):
    # base_url that results in empty base (e.g., "https://") should return None and log specific error
    self_obj = types.SimpleNamespace()
    self_obj.gitea_access_token = "TOKEN"
    self_obj.base_url = "https://"

    result, logger = _call_prepare(monkeypatch, self_obj, "https://gitea.example.com/user/repo.git")

    assert result is None
    assert logger.errors, "Expected an error to be logged when base url part is empty"
    assert f"Base url: {self_obj.base_url} has an empty base url" in logger.errors[0]


def test_prepare_clone_url_base_not_in_repo(monkeypatch):
    # When the base (host) is not present in repo URL, return None and log message
    self_obj = types.SimpleNamespace()
    self_obj.gitea_access_token = "TOKEN"
    self_obj.base_url = "https://gitea.example.com"

    repo_url = "https://other.example.com/user/repo.git"
    result, logger = _call_prepare(monkeypatch, self_obj, repo_url)

    assert result is None
    assert logger.errors, "Expected an error to be logged when repo URL doesn't contain base"
    # base used in the error is the part after scheme
    expected_base = self_obj.base_url.split(self_obj.base_url.split("://")[0] + "://")[1]
    assert f"url to clone: {repo_url} does not contain {expected_base}" in logger.errors[0]


def test_prepare_clone_url_repo_full_name_empty(monkeypatch):
    # If repo URL ends exactly at the base (no repo path), method should log malformed URL and return None
    self_obj = types.SimpleNamespace()
    self_obj.gitea_access_token = "TOKEN"
    self_obj.base_url = "https://gitea.example.com"

    repo_url = "https://gitea.example.com"  # no trailing path -> repo_full_name becomes empty
    result, logger = _call_prepare(monkeypatch, self_obj, repo_url)

    assert result is None
    assert logger.errors, "Expected an error to be logged for malformed repo URL"
    assert f"url to clone: {repo_url} is malformed" in logger.errors[0]


def test_prepare_clone_url_success(monkeypatch):
    # Successful creation of clone URL embeds token correctly
    self_obj = types.SimpleNamespace()
    self_obj.gitea_access_token = "MY_TOKEN_123"
    self_obj.base_url = "https://gitea.example.com"

    repo_url = "https://gitea.example.com/user/repo.git"
    result, logger = _call_prepare(monkeypatch, self_obj, repo_url)

    assert logger.errors == []  # no errors logged
    expected_base = self_obj.base_url.split(self_obj.base_url.split("://")[0] + "://")[1]
    expected = self_obj.base_url.split("://")[0] + "://" + f"{self_obj.gitea_access_token}@{expected_base}/user/repo.git"
    assert result == expected
