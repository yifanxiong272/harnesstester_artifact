# file: pr_agent/git_providers/gitea_provider.py:21-102
# asked: {"lines": [22, 23, 25, 26, 27, 29, 30, 31, 33, 34, 35, 36, 38, 39, 40, 41, 43, 44, 47, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 84, 86, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 98, 99, 100, 102], "branches": [[25, 26], [25, 29], [34, 35], [34, 38], [43, 44], [43, 47], [69, 70], [69, 97], [97, 98], [97, 102]]}
# gained: {"lines": [22, 23, 25, 26, 27, 29, 30, 31, 33, 34, 35, 36, 38, 39, 40, 41, 43, 47, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 84, 86, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 98, 99, 100], "branches": [[25, 26], [25, 29], [34, 35], [34, 38], [43, 47], [69, 70], [69, 97], [97, 98]]}

import types
import pytest

import pr_agent.git_providers.gitea_provider as gp


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)

    def info(self, msg):
        pass

    def debug(self, msg):
        pass


class FakeConfiguration:
    def __init__(self):
        self.host = None
        self.api_key = {'Authorization': None}
        self.verify_ssl = True
        self.ssl_ca_cert = None


class FakeApiClient:
    def __init__(self, configuration):
        self.configuration = configuration


class FakePRObject:
    def __init__(self, head_sha="headsha", base_sha="basesha", base_ref="main"):
        class Head:
            def __init__(self, sha):
                self.sha = sha

        class Base:
            def __init__(self, sha, ref):
                self.sha = sha
                self.ref = ref

        self.head = Head(head_sha)
        self.base = Base(base_sha, base_ref)


class FakeRepoApi:
    def __init__(self, client):
        self.client = client
        # record last call args for assertions if needed
        self.last_called = {}

    def get_pull_request(self, owner, repo, pr_number):
        self.last_called['get_pull_request'] = (owner, repo, pr_number)
        return FakePRObject(head_sha="commit_sha_123", base_sha="base_sha_000", base_ref="develop")

    def get_change_file_pull_request(self, owner, repo, pr_number):
        self.last_called['get_change_file_pull_request'] = (owner, repo, pr_number)
        # return a sample of changed files
        return [{"filename": "a.txt"}, {"filename": "b.py"}]

    def list_all_commits(self, owner, repo):
        self.last_called['list_all_commits'] = (owner, repo)
        return ["commit1", "commit2", "commit3"]


def make_settings(token_value=None, base_url="https://gitea.example", skip_ssl=False, ssl_ca_cert=None):
    # return a dict-like object that has .get
    d = {
        "GITEA.URL": base_url,
        "GITEA.PERSONAL_ACCESS_TOKEN": token_value,
        "GITEA.REPO_SETTING": None,
        "GITEA.SKIP_SSL_VERIFICATION": skip_ssl,
        "GITEA.SSL_CA_CERT": ssl_ca_cert,
    }
    return d


def test_init_raises_when_no_url(monkeypatch):
    # Arrange: ensure logger records errors
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy_logger)

    # Act & Assert
    with pytest.raises(ValueError) as exc:
        gp.GiteaProvider(None)

    assert "PR URL not provided." in str(exc.value)
    # ensure logger.error was called with the expected message
    assert dummy_logger.errors and "PR URL not provided." in dummy_logger.errors[0]


def test_init_raises_when_no_token(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy_logger)
    # settings missing token
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(token_value=None))

    # Provide a URL so we pass the first check but fail the token check
    with pytest.raises(ValueError) as exc:
        gp.GiteaProvider("https://gitea.example/pulls/1")

    assert "Gitea access token not found in settings." in str(exc.value)
    assert dummy_logger.errors and "Gitea access token not found in settings." in dummy_logger.errors[0]


def test_init_pull_request_flow(monkeypatch):
    # Arrange: provide settings with token
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(token_value="secrettoken"))
    # Logger
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy_logger)

    # Replace giteapy module attributes used in the constructor
    fake_giteapy = types.SimpleNamespace(Configuration=FakeConfiguration, ApiClient=FakeApiClient)
    monkeypatch.setattr(gp, "giteapy", fake_giteapy)

    # Replace RepoApi with our fake
    monkeypatch.setattr(gp, "RepoApi", FakeRepoApi)

    # make filter_ignored identity (it is imported in module)
    monkeypatch.setattr(gp, "filter_ignored", lambda files, platform=None: files)

    # Prevent private helpers from parsing real URLs; instead set owner/repo/pr_number directly
    def fake_set_repo_and_owner_from_pr(self):
        self.owner = "owner1"
        self.repo = "repo1"
        self.pr_number = 42

    monkeypatch.setattr(gp.GiteaProvider, "_GiteaProvider__set_repo_and_owner_from_pr", fake_set_repo_and_owner_from_pr)

    # stub out __add_file_content and __add_file_diff so they do not rely on external calls
    monkeypatch.setattr(gp.GiteaProvider, "_GiteaProvider__add_file_content", lambda self: setattr(self, "file_contents", {"a.txt": "content"}))
    monkeypatch.setattr(gp.GiteaProvider, "_GiteaProvider__add_file_diff", lambda self: setattr(self, "file_diffs", {"a.txt": "diff"}))

    # Act
    url = "https://gitea.example/pulls/123"
    provider = gp.GiteaProvider(url)

    # Assert basic attributes set by the constructor flow
    assert provider.enabled_pr is True
    assert provider.pr_url == url
    # repo_api should be our FakeRepoApi instance
    assert isinstance(provider.repo_api, FakeRepoApi)
    # git_files should be as returned by FakeRepoApi.get_change_file_pull_request
    assert provider.git_files == [{"filename": "a.txt"}, {"filename": "b.py"}]
    # sha should come from FakePRObject.head.sha
    assert provider.sha == "commit_sha_123"
    # pr_commits should be the fake list
    assert provider.pr_commits == ["commit1", "commit2", "commit3"]
    # last_commit should be the last element
    assert provider.last_commit == "commit3"
    assert provider.last_commit_id == "commit3"
    # base_sha and base_ref from FakePRObject.base
    assert provider.base_sha == "base_sha_000"
    assert provider.base_ref == "develop"
    # file_contents/file_diffs set by our stubbed helpers
    assert provider.file_contents == {"a.txt": "content"}
    assert provider.file_diffs == {"a.txt": "diff"}


def test_init_issue_flow(monkeypatch):
    # Arrange: provide settings with token
    monkeypatch.setattr(gp, "get_settings", lambda: make_settings(token_value="token123"))
    dummy_logger = DummyLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: dummy_logger)

    # Provide minimal giteapy and RepoApi (not used for issues path in constructor)
    fake_giteapy = types.SimpleNamespace(Configuration=FakeConfiguration, ApiClient=FakeApiClient)
    monkeypatch.setattr(gp, "giteapy", fake_giteapy)
    monkeypatch.setattr(gp, "RepoApi", FakeRepoApi)

    # stub __set_repo_and_owner_from_issue to avoid parsing
    def fake_set_repo_and_owner_from_issue(self):
        self.owner = "ownerX"
        self.repo = "repoX"
        self.issue_number = 7

    monkeypatch.setattr(gp.GiteaProvider, "_GiteaProvider__set_repo_and_owner_from_issue", fake_set_repo_and_owner_from_issue)

    # Act
    issue_url = "https://gitea.example/issues/7"
    provider = gp.GiteaProvider(issue_url)

    # Assert
    assert provider.issue_url == issue_url
    assert provider.enabled_issue is True
    # For issues branch, constructor may not set pr_commits attribute at all
    assert not hasattr(provider, "pr_commits")
    # ensure owner/repo/issue_number set by our stub
    assert provider.owner == "ownerX"
    assert provider.repo == "repoX"
    assert provider.issue_number == 7
