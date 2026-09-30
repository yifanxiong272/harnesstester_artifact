import pytest

from pr_agent.git_providers.gitea_provider import GiteaProvider


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # mirror real logger API minimally
        self.errors.append(msg)


def test_init_no_url_round_023(monkeypatch):
    """When no URL is provided, constructor should log an error and raise ValueError."""
    logger = DummyLogger()
    # Patch get_logger so the provider uses our dummy
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.get_logger", lambda: logger
    )

    with pytest.raises(ValueError) as excinfo:
        # empty/None url triggers the first error branch
        GiteaProvider(url=None)

    assert "PR URL not provided." in str(excinfo.value)
    # last logged error should match
    assert logger.errors and logger.errors[-1] == "PR URL not provided."


def test_init_token_missing_round_023(monkeypatch):
    """When token is missing in settings, constructor should log an error and raise ValueError."""
    logger = DummyLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.get_logger", lambda: logger
    )

    # Return settings with no personal access token
    def fake_settings():
        return {
            "GITEA.URL": "https://gitea.example",
            "GITEA.PERSONAL_ACCESS_TOKEN": None,
        }

    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.get_settings", fake_settings
    )

    with pytest.raises(ValueError) as excinfo:
        # non-empty URL so it progresses past initial URL check
        GiteaProvider(url="https://gitea.example/pulls/1")

    assert "Gitea access token not found in settings." in str(excinfo.value)
    assert logger.errors and logger.errors[-1] == "Gitea access token not found in settings."


def test_init_pull_request_flow_round_023(monkeypatch):
    """Simulate a pull-request URL flow with a working token and repository API.

    This test patches giteapy.Configuration, giteapy.ApiClient, RepoApi, filter_ignored,
    and GiteaProvider private methods to exercise the 'pulls' branch and
    behavior that depends on model-derived/config settings.
    """
    logger = DummyLogger()
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.get_logger", lambda: logger
    )

    settings = {
        "GITEA.URL": "https://gitea.example",
        "GITEA.PERSONAL_ACCESS_TOKEN": "tok",
        "GITEA.REPO_SETTING": None,
        "GITEA.SKIP_SSL_VERIFICATION": True,
        "GITEA.SSL_CA_CERT": "/path/cert.pem",
    }

    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.get_settings", lambda: settings
    )

    # Dummy Configuration that records the last instance created for assertions
    class DummyConfig:
        last_instance = None

        def __init__(self):
            self.api_key = {}
            self.host = None
            self.verify_ssl = True
            self.ssl_ca_cert = None
            DummyConfig.last_instance = self

    class DummyApiClient:
        def __init__(self, config):
            # just preserve config for possible inspection
            self.config = config

    # Build minimal PR-like objects used by the constructor
    class PRHead:
        def __init__(self, sha):
            self.sha = sha

    class PRBase:
        def __init__(self, sha, ref):
            self.sha = sha
            self.ref = ref

    class DummyPR:
        def __init__(self):
            self.head = PRHead("headsha")
            self.base = PRBase("basesha", "base_ref")

    class DummyRepoApi:
        def __init__(self, client):
            self.client = client

        def get_pull_request(self, owner, repo, pr_number):
            # return an object with head/base used by constructor
            return DummyPR()

        def get_change_file_pull_request(self, owner, repo, pr_number):
            # return list of changed files
            return ["a.py"]

        def list_all_commits(self, owner, repo):
            # return commits so last_commit picks last element
            return ["commit1", "commit2"]

    # Patch giteapy and RepoApi references used in the module
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.giteapy.Configuration", DummyConfig
    )
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.giteapy.ApiClient", DummyApiClient
    )
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.RepoApi", DummyRepoApi
    )

    # Ensure filter_ignored is predictable (identity)
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.filter_ignored", lambda files, platform=None: files
    )

    # Patch private helper __set_repo_and_owner_from_pr to populate owner/repo/pr_number
    def fake_set_repo_and_owner_from_pr(self):
        self.owner = "owner1"
        self.repo = "repo1"
        self.pr_number = 123

    # Patch private add content/diff methods to no-op to avoid deeper calls
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.GiteaProvider._GiteaProvider__set_repo_and_owner_from_pr",
        fake_set_repo_and_owner_from_pr,
        raising=False,
    )
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.GiteaProvider._GiteaProvider__add_file_content",
        lambda self: None,
        raising=False,
    )
    monkeypatch.setattr(
        "pr_agent.git_providers.gitea_provider.GiteaProvider._GiteaProvider__add_file_diff",
        lambda self: None,
        raising=False,
    )

    # Now instantiate with a 'pulls' URL to exercise that branch
    provider = GiteaProvider(url="https://gitea.example/pulls/1")

    # Verify attributes set by the 'pulls' branch
    assert provider.pr_url == "https://gitea.example/pulls/1"
    assert provider.enabled_pr is True
    assert provider.pr is not None
    assert provider.git_files == ["a.py"]
    assert provider.sha == "headsha"
    assert provider.pr_commits == ["commit1", "commit2"]
    assert provider.last_commit == "commit2"
    assert provider.last_commit_id == "commit2"
    assert provider.base_sha == "basesha"
    assert provider.base_ref == "base_ref"

    # Verify configuration was mutated according to settings
    cfg = DummyConfig.last_instance
    assert cfg is not None
    assert cfg.verify_ssl is False
    assert cfg.ssl_ca_cert == "/path/cert.pem"
    # api_key Authorization must have been set to token <tok>
    assert cfg.api_key.get("Authorization") == "token tok"
