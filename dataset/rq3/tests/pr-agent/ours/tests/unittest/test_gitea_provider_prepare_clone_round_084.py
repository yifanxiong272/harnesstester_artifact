import pytest
import pr_agent.git_providers.gitea_provider as gitea_mod
from pr_agent.git_providers.gitea_provider import GiteaProvider


class DummyLogger:
    def __init__(self):
        self.messages = []

    def error(self, msg: str) -> None:
        # capture the exact error messages for assertions
        self.messages.append(msg)


def _make_provider(monkeypatch, base_url="https://gitea.example.com", token="tok"):
    """Helper to create a GiteaProvider and patch the module logger and settings.

    Important: patch get_settings to include a PERSONAL_ACCESS_TOKEN so __init__ does
    not raise. After instantiation, override provider attributes to the desired test values.
    """
    logger = DummyLogger()
    # patch the module-level get_logger used by the function under test
    monkeypatch.setattr(gitea_mod, "get_logger", lambda: logger)
    # patch get_settings so __init__ finds a token and does not raise
    monkeypatch.setattr(gitea_mod, "get_settings", lambda: {"GITEA.PERSONAL_ACCESS_TOKEN": token})
    # instantiate with a harmless url (must be truthy)
    prov = GiteaProvider("https://irrelevant.example.com")
    # set attributes to control behavior of _prepare_clone_url_with_token
    prov.gitea_access_token = token
    prov.base_url = base_url
    return prov, logger


def test_missing_token_or_base_url_round_084(monkeypatch):
    # both token and base_url missing at call time should return None and log exact error
    # Ensure provider is created with a valid token (to avoid __init__ raising), then
    # simulate missing attributes by setting them to None before calling the method.
    prov, logger = _make_provider(monkeypatch, base_url="https://gitea.example.com", token="goodtoken")
    prov.gitea_access_token = None
    prov.base_url = None

    result = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")

    assert result is None
    assert logger.messages == ["Either missing auth token or missing base url"]


def test_empty_base_url_after_scheme_round_084(monkeypatch):
    # base_url like "https://" (set on the instance) leads to empty base_url after splitting -> specific error
    prov, logger = _make_provider(monkeypatch, base_url="https://", token="mytoken")

    result = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")

    assert result is None
    assert logger.messages == [f"Base url: {prov.base_url} has an empty base url"]


def test_repo_url_not_containing_base_round_084(monkeypatch):
    # repo_url_to_clone does not contain the base_url -> logs that fact and returns None
    prov, logger = _make_provider(monkeypatch, base_url="https://gitea.example.com", token="t")
    repo_url = "https://otherhost.example.org/owner/repo.git"

    result = prov._prepare_clone_url_with_token(repo_url)

    # expected base_url used inside function is the part after the scheme
    expected_base = prov.base_url.split("://")[1] if "://" in prov.base_url else prov.base_url
    assert result is None
    assert logger.messages == [f"url to clone: {repo_url} does not contain {expected_base}"]


def test_repo_full_name_empty_round_084(monkeypatch):
    # repo_url_to_clone that ends exactly at base_url yields empty repo_full_name -> malformed
    prov, logger = _make_provider(monkeypatch, base_url="https://gitea.example.com", token="tok123")
    # this URL contains the base but nothing after it -> repo_full_name becomes empty
    repo_url = prov.base_url

    result = prov._prepare_clone_url_with_token(repo_url)

    assert result is None
    assert logger.messages == [f"url to clone: {repo_url} is malformed"]


def test_success_prepare_clone_url_round_084(monkeypatch):
    # valid inputs produce the token-embedded clone url
    base = "https://gitea.example.com"
    token = "token123"
    prov, logger = _make_provider(monkeypatch, base_url=base, token=token)

    repo_url = "https://gitea.example.com/owner/repo.git"
    result = prov._prepare_clone_url_with_token(repo_url)

    # compute expected parts the same way the function does
    scheme = prov.base_url.split("://")[0] + "://"
    expected_base = prov.base_url.split(scheme)[1]
    expected_repo_full = repo_url.split(expected_base)[-1]
    expected_clone_url = scheme + f"{token}@{expected_base}{expected_repo_full}"

    assert result == expected_clone_url
    # success path should not log an error
    assert logger.messages == []
