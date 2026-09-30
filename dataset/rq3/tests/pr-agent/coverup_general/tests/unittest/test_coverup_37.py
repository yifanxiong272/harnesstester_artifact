# file: pr_agent/git_providers/github_provider.py:827-852
# asked: {"lines": [828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 852], "branches": [[830, 831], [830, 841], [836, 837], [836, 838], [841, 842], [841, 849], [849, 850], [849, 852]]}
# gained: {"lines": [828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 852], "branches": [[830, 831], [830, 841], [836, 837], [836, 838], [841, 842], [841, 849], [849, 850], [849, 852]]}

import pytest
from types import SimpleNamespace

import pr_agent.git_providers.github_provider as gp
from pr_agent.git_providers.github_provider import GithubProvider


class DummySettings:
    def __init__(self, deployment_type='user', github_attrs=None, base_url='https://api.github.com'):
        self._map = {'GITHUB.DEPLOYMENT_TYPE': deployment_type, 'GITHUB.BASE_URL': base_url}
        self.github = SimpleNamespace(**(github_attrs or {}))

    def get(self, key, default=None):
        return self._map.get(key, default)


class DummyAppAuthentication:
    def __init__(self, app_id=None, private_key=None, installation_id=None):
        self.app_id = app_id
        self.private_key = private_key
        self.installation_id = installation_id


class DummyToken:
    def __init__(self, token):
        self.token = token


class DummyAuthNamespace:
    Token = DummyToken


class DummyGithubClient:
    def __init__(self, auth=None, base_url=None):
        self.auth = auth
        self.base_url = base_url


def test_user_missing_token_raises(monkeypatch):
    # deployment_type 'user' but no github.user_token attribute -> should raise ValueError
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='user', github_attrs={}))
    # ensure Auth/Github/AppAuthentication not used unexpectedly
    monkeypatch.setattr(gp, "Auth", DummyAuthNamespace)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)
    with pytest.raises(ValueError) as exc:
        GithubProvider()
    assert "GitHub token is required when using user deployment" in str(exc.value)


def test_user_with_token_returns_github_client(monkeypatch):
    # deployment_type 'user' with token should set Auth.Token and return Github client
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='user', github_attrs={"user_token": "secrettok"}, base_url="https://api.example.com"))
    # patch Auth.Token and Github to dummy classes to capture inputs
    monkeypatch.setattr(gp, "Auth", DummyAuthNamespace)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)

    provider = GithubProvider()
    # provider.auth should be DummyToken with token
    assert isinstance(provider.auth, DummyToken)
    assert provider.auth.token == "secrettok"
    # provider.github_client should be DummyGithubClient and have matching auth and base_url
    assert isinstance(provider.github_client, DummyGithubClient)
    assert provider.github_client.auth is provider.auth
    assert provider.github_client.base_url == "https://api.example.com"


def test_app_missing_github_attrs_raises(monkeypatch):
    # deployment_type 'app' but github object missing private_key/app_id -> should raise ValueError
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='app', github_attrs={}))
    monkeypatch.setattr(gp, "AppAuthentication", DummyAppAuthentication)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)
    with pytest.raises(ValueError) as exc:
        GithubProvider()
    assert "GitHub app ID and private key are required when using GitHub app deployment" in str(exc.value)


def test_app_missing_installation_id_raises(monkeypatch):
    # deployment_type 'app' with app_id/private_key but no installation_id in context -> should raise ValueError
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='app', github_attrs={"app_id": "42", "private_key": "keybytes"}))
    monkeypatch.setattr(gp, "AppAuthentication", DummyAppAuthentication)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)
    # ensure context.get returns None (default behavior) by monkeypatching context.get
    monkeypatch.setattr(gp, "context", SimpleNamespace(get=lambda key, default=None: None))
    with pytest.raises(ValueError) as exc:
        GithubProvider()
    assert "GitHub app installation ID is required when using GitHub app deployment" in str(exc.value)


def test_app_with_all_sets_auth_and_returns_github(monkeypatch):
    # deployment_type 'app' with app_id/private_key and installation_id present -> should set AppAuthentication and return Github
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='app', github_attrs={"app_id": "99", "private_key": "priv"} , base_url="https://api.custom.com"))
    monkeypatch.setattr(gp, "AppAuthentication", DummyAppAuthentication)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)
    # context.get returns an installation id
    monkeypatch.setattr(gp, "context", SimpleNamespace(get=lambda key, default=None: 777))

    provider = GithubProvider()
    # provider.auth should be DummyAppAuthentication and have the values passed
    assert isinstance(provider.auth, DummyAppAuthentication)
    assert provider.auth.app_id == "99"
    assert provider.auth.private_key == "priv"
    assert provider.auth.installation_id == 777
    # provider.github_client should be DummyGithubClient and have auth and base_url set
    assert isinstance(provider.github_client, DummyGithubClient)
    assert provider.github_client.auth is provider.auth
    assert provider.github_client.base_url == "https://api.custom.com"


def test_unknown_deployment_type_raises(monkeypatch):
    # deployment_type unknown should leave auth None and raise ValueError("Could not authenticate to GitHub")
    monkeypatch.setattr(gp, "get_settings", lambda: DummySettings(deployment_type='weird', github_attrs={}))
    # patch Auth/AppAuthentication/Github to ensure they're available if called
    monkeypatch.setattr(gp, "AppAuthentication", DummyAppAuthentication)
    monkeypatch.setattr(gp, "Auth", DummyAuthNamespace)
    monkeypatch.setattr(gp, "Github", DummyGithubClient)
    with pytest.raises(ValueError) as exc:
        GithubProvider()
    assert "Could not authenticate to GitHub" in str(exc.value)
