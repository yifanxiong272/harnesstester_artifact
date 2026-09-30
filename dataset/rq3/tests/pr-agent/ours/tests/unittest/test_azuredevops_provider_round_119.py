import pytest
from types import SimpleNamespace

import pr_agent.git_providers.azuredevops_provider as azuredevops_provider
from pr_agent.git_providers.azuredevops_provider import AzureDevopsProvider


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class FakeBasicAuth:
    def __init__(self, username, token):
        # preserve shape: store passed values for assertions
        self.username = username
        self.token = token


class FakeConnection:
    def __init__(self, base_url, creds):
        # preserve shape: store passed values for assertions
        self.base_url = base_url
        self.creds = creds
        # clients object with required methods
        self.clients = SimpleNamespace(
            get_git_client=lambda: "GIT_CLIENT",
            get_work_item_tracking_client=lambda: "BOARD_CLIENT",
        )


class FakeDefaultCredsSuccess:
    def get_token(self, _):
        # return object with .token attribute as expected by code under test
        return SimpleNamespace(token="DEFAULT_TOKEN_123")


class FakeDefaultCredsFail:
    def get_token(self, _):
        raise RuntimeError("credential error")


def make_settings(azure_devops_dict):
    # get_settings() in module returns object with .azure_devops attribute
    return SimpleNamespace(azure_devops=azure_devops_dict)


def test_missing_org_round_119(monkeypatch):
    # Arrange: settings with no org
    monkeypatch.setattr(azuredevops_provider, "get_settings", lambda: make_settings({}))
    # Act & Assert: should raise ValueError when org missing
    with pytest.raises(ValueError) as excinfo:
        AzureDevopsProvider._get_azure_devops_client()
    assert "Azure DevOps organization is required" in str(excinfo.value)


def test_pat_present_round_119(monkeypatch):
    # Arrange: settings with org and pat
    settings = make_settings({"org": "https://dev.azure.com/example", "pat": "MY_PAT"})
    monkeypatch.setattr(azuredevops_provider, "get_settings", lambda: settings)

    # Patch logger so we can assert no fallback logging occurred
    fake_logger = FakeLogger()
    monkeypatch.setattr(azuredevops_provider, "get_logger", lambda: fake_logger)

    # Ensure DefaultAzureCredential is not used: set to callable that would fail if called
    def default_cred_called():
        raise AssertionError("DefaultAzureCredential was called unexpectedly")

    monkeypatch.setattr(azuredevops_provider, "DefaultAzureCredential", default_cred_called)

    # Patch BasicAuthentication and Connection to controlled fakes
    created_basic_auth = {}

    def fake_basic_auth(username, token):
        created_basic_auth['instance'] = FakeBasicAuth(username, token)
        return created_basic_auth['instance']

    monkeypatch.setattr(azuredevops_provider, "BasicAuthentication", fake_basic_auth)
    monkeypatch.setattr(azuredevops_provider, "Connection", FakeConnection)

    # Act
    git_client, board_client = AzureDevopsProvider._get_azure_devops_client()

    # Assert: clients come from our FakeConnection
    assert git_client == "GIT_CLIENT"
    assert board_client == "BOARD_CLIENT"
    # BasicAuthentication must have been called with empty username and the PAT
    assert 'instance' in created_basic_auth
    assert created_basic_auth['instance'].username == ""
    assert created_basic_auth['instance'].token == "MY_PAT"
    # No fallback logging should have been recorded
    assert fake_logger.infos == []
    assert fake_logger.errors == []


def test_default_credential_success_round_119(monkeypatch):
    # Arrange: settings with org but no pat
    settings = make_settings({"org": "https://dev.azure.com/example"})
    monkeypatch.setattr(azuredevops_provider, "get_settings", lambda: settings)

    # Patch logger to capture info call
    fake_logger = FakeLogger()
    monkeypatch.setattr(azuredevops_provider, "get_logger", lambda: fake_logger)

    # Patch DefaultAzureCredential to our fake that returns a token
    monkeypatch.setattr(azuredevops_provider, "DefaultAzureCredential", lambda: FakeDefaultCredsSuccess())

    # Patch BasicAuthentication and Connection
    captured = {}

    def fake_basic_auth(username, token):
        captured['auth'] = FakeBasicAuth(username, token)
        return captured['auth']

    monkeypatch.setattr(azuredevops_provider, "BasicAuthentication", fake_basic_auth)
    monkeypatch.setattr(azuredevops_provider, "Connection", FakeConnection)

    # Act
    git_client, board_client = AzureDevopsProvider._get_azure_devops_client()

    # Assert
    assert git_client == "GIT_CLIENT"
    assert board_client == "BOARD_CLIENT"
    # BasicAuthentication should be called with token returned from DefaultAzureCredential
    assert 'auth' in captured
    assert captured['auth'].token == "DEFAULT_TOKEN_123"
    # Logger should have an info message about trying default credentials
    assert any("trying to use Azure Default Credentials" in msg or "No PAT found in settings" in msg for msg in fake_logger.infos)


def test_default_credential_failure_round_119(monkeypatch):
    # Arrange: settings with org but no pat
    settings = make_settings({"org": "https://dev.azure.com/example"})
    monkeypatch.setattr(azuredevops_provider, "get_settings", lambda: settings)

    # Patch logger to capture error
    fake_logger = FakeLogger()
    monkeypatch.setattr(azuredevops_provider, "get_logger", lambda: fake_logger)

    # Patch DefaultAzureCredential to our failing fake
    monkeypatch.setattr(azuredevops_provider, "DefaultAzureCredential", lambda: FakeDefaultCredsFail())

    # Patch BasicAuthentication and Connection to ensure they are not reached after failure
    monkeypatch.setattr(azuredevops_provider, "BasicAuthentication", lambda u, t: (_ for _ in ()).throw(AssertionError("BasicAuthentication should not be called")))
    monkeypatch.setattr(azuredevops_provider, "Connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Connection should not be called")))

    # Act & Assert: the credential error should propagate
    with pytest.raises(RuntimeError) as excinfo:
        AzureDevopsProvider._get_azure_devops_client()
    assert "credential error" in str(excinfo.value)
    # Logger.error should have been called with a message including our exception text
    assert any("Azure Default Authentication failed" in msg or "credential error" in msg for msg in fake_logger.errors)
