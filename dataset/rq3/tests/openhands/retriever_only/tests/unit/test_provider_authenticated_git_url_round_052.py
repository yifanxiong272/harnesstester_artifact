import os
import pytest

from openhands.integrations.provider import ProviderHandler, ProviderType


class _DummyToken:
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


class _DummyProviderToken:
    def __init__(self, token_value: str, host: str | None = None):
        self.token = _DummyToken(token_value)
        self.host = host


class _DummyRepo:
    def __init__(self, full_name: str, git_provider):
        self.full_name = full_name
        self.git_provider = git_provider


class _FakeSelf:
    def __init__(self, provider, domain_mapping=None, provider_tokens=None, repo=None):
        # mimic attributes used by get_authenticated_git_url
        self.PROVIDER_DOMAINS = domain_mapping or {}
        self.provider_tokens = provider_tokens
        self._repo = repo

    async def verify_repo_provider(self, repo_name: str, is_optional: bool = False):
        # return the prepared repo object (mimic successful verification)
        return self._repo


@pytest.mark.asyncio
async def test_http_insecure_disallowed_round_052(monkeypatch):
    """If domain starts with http:// and ALLOW_INSECURE_GIT_ACCESS is not truthy, a ValueError is raised.

    Covers branch: domain startswith http -> check env -> not allowed -> raise
    """
    # Ensure env var is not set to allow insecure access
    monkeypatch.delenv("ALLOW_INSECURE_GIT_ACCESS", raising=False)

    provider = ProviderType.GITHUB
    domain_map = {provider: "http://github.example.com"}
    repo = _DummyRepo(full_name="owner/repo", git_provider=provider)
    fake_self = _FakeSelf(provider, domain_mapping=domain_map, provider_tokens=None, repo=repo)

    with pytest.raises(ValueError):
        await ProviderHandler.get_authenticated_git_url(fake_self, repo_name="owner/repo")


@pytest.mark.asyncio
async def test_http_insecure_allowed_gitlab_round_052(monkeypatch):
    """When ALLOW_INSECURE_GIT_ACCESS is enabled, http protocol is allowed and GitLab oauth2 URL is constructed.

    Covers: allow_insecure path, protocol='http', normalization, GitLab token URL pattern
    """
    monkeypatch.setenv("ALLOW_INSECURE_GIT_ACCESS", "true")

    provider = ProviderType.GITLAB
    # Domain explicitly includes http:// to trigger insecure branch
    domain_map = {provider: "http://gitlab.example.com"}
    # token value used by get_secret_value
    provider_tokens = {provider: _DummyProviderToken(token_value="tok", host=None)}
    repo = _DummyRepo(full_name="owner/repo", git_provider=provider)
    fake_self = _FakeSelf(provider, domain_mapping=domain_map, provider_tokens=provider_tokens, repo=repo)

    url = await ProviderHandler.get_authenticated_git_url(fake_self, repo_name="owner/repo")

    assert url == "http://oauth2:tok@gitlab.example.com/owner/repo.git"


@pytest.mark.asyncio
async def test_bitbucket_data_center_with_colon_creds_round_052():
    """Bitbucket Data Center should accept username:password token, percent-encode credentials and construct SCM path.

    Covers: BITBUCKET_DATA_CENTER branch, token with ':', domain normalization (strip protocol and path), scm path construction, percent-encoding
    """
    provider = ProviderType.BITBUCKET_DATA_CENTER
    # Include protocol and path to ensure normalization and split at '/'
    domain_map = {provider: "https://bbdc.example.com/api/v1"}
    # token contains ':' to trigger user:pass split and contains characters to be percent-encoded
    raw_token = "user:pa$$/word"
    provider_tokens = {provider: _DummyProviderToken(token_value=raw_token, host=None)}
    repo = _DummyRepo(full_name="Project/Repo-Slug", git_provider=provider)
    fake_self = _FakeSelf(provider, domain_mapping=domain_map, provider_tokens=provider_tokens, repo=repo)

    url = await ProviderHandler.get_authenticated_git_url(fake_self, repo_name="Project/Repo-Slug")

    # Manually construct expected percent-encoded credentials
    from urllib.parse import quote

    expected_user = quote("user", safe="")
    expected_pass = quote("pa$$/word", safe="")
    expected_creds = f"{expected_user}:{expected_pass}"
    expected_domain = "bbdc.example.com"
    expected_scm = "scm/project/Repo-Slug.git"
    expected_url = f"https://{expected_creds}@{expected_domain}/{expected_scm}"

    assert url == expected_url


@pytest.mark.asyncio
async def test_azure_devops_fallback_repo_format_round_052():
    """Azure DevOps fallback path when repo name doesn't have org/project/repo (len < 3).

    Covers: AZURE_DEVOPS branch fallback (len(parts) < 3) building fallback URL
    """
    provider = ProviderType.AZURE_DEVOPS
    domain_map = {provider: "https://dev.azure.com"}
    provider_tokens = {provider: _DummyProviderToken(token_value="PATTOKEN", host=None)}
    # repo_name that does not split into 3 parts triggers the fallback
    repo = _DummyRepo(full_name="myrepo", git_provider=provider)
    fake_self = _FakeSelf(provider, domain_mapping=domain_map, provider_tokens=provider_tokens, repo=repo)

    url = await ProviderHandler.get_authenticated_git_url(fake_self, repo_name="myrepo")

    assert url == "https://user:PATTOKEN@dev.azure.com/myrepo.git"
