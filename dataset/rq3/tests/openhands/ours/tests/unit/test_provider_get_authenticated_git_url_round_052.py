import os
import asyncio
from urllib.parse import quote as _quote
import pytest

from openhands.integrations import provider as provider_mod
from openhands.integrations.provider import ProviderHandler
from openhands.integrations.service_types import ProviderType


class FakeSecret:
    def __init__(self, value: str | None):
        self._value = value

    def get_secret_value(self) -> str | None:
        return self._value


class FakeProviderToken:
    def __init__(self, token: FakeSecret | None = None, host: str | None = None):
        self.token = token
        self.host = host


class FakeRepo:
    def __init__(self, provider, full_name: str):
        self.git_provider = provider
        self.full_name = full_name


class DummySelf:
    """A minimal object to serve as `self` when binding the unbound
    ProviderHandler.get_authenticated_git_url function.

    It provides only attributes and methods referenced by that function.
    """

    def __init__(self, provider_tokens=None, provider_domains=None):
        # provider_tokens: mapping ProviderType -> FakeProviderToken
        self.provider_tokens = provider_tokens or {}
        # PROVIDER_DOMAINS mapping used by the method
        self.PROVIDER_DOMAINS = provider_domains or {}

    async def verify_repo_provider(self, repo_name: str, is_optional: bool = False):
        # The tests pass the repo_name as the string used to create the repository
        # object for simplicity. In the real class this would validate and return
        # a Repository object. We create a FakeRepo with the provider already set
        # in the DummySelf instance for each test by setting an attribute on self.
        return self._repo


async def _call_get_url(dummy_self: DummySelf, repo_name: str, is_optional: bool = False):
    # Bind the unbound function from ProviderHandler to our dummy_self and call it
    fn = ProviderHandler.get_authenticated_git_url.__get__(dummy_self, ProviderHandler)
    return await fn(repo_name, is_optional=is_optional)


@pytest.mark.asyncio
async def test_insecure_http_disallowed_round_052(monkeypatch):
    # Domain starts with http:// and ALLOW_INSECURE_GIT_ACCESS is not truthy -> ValueError
    monkeypatch.delenv('ALLOW_INSECURE_GIT_ACCESS', raising=False)

    provider = ProviderType.GITHUB
    domains = {provider: 'http://insecure.example.com/path'}

    dummy = DummySelf(provider_tokens={}, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'owner/repo')

    with pytest.raises(ValueError):
        await _call_get_url(dummy, 'owner/repo')


@pytest.mark.asyncio
async def test_insecure_http_allowed_gitlab_round_052(monkeypatch):
    # Allow insecure HTTP via env var -> should build an http:// oauth2:token URL for GitLab
    monkeypatch.setenv('ALLOW_INSECURE_GIT_ACCESS', 'true')

    provider = ProviderType.GITLAB
    # host contains path to ensure normalization logic strips path segments
    domains = {provider: 'http://gitlab.example.com/api/v4'}

    fake_token = FakeSecret('gl-token')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'owner/repo')

    url = await _call_get_url(dummy, 'ignored')
    assert url == 'http://oauth2:gl-token@gitlab.example.com/owner/repo.git'


@pytest.mark.asyncio
async def test_bitbucket_with_colon_round_052():
    # Bitbucket token in username:app_password format -> inserted directly before @domain
    provider = ProviderType.BITBUCKET
    domains = {provider: 'https://bitbucket.org'}

    fake_token = FakeSecret('alice:app_password')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'owner/repo')

    url = await _call_get_url(dummy, 'owner/repo')
    assert url == 'https://alice:app_password@bitbucket.org/owner/repo.git'


@pytest.mark.asyncio
async def test_bitbucket_without_colon_round_052():
    # Bitbucket token as access token -> use x-token-auth:token
    provider = ProviderType.BITBUCKET
    domains = {provider: 'https://bitbucket.org'}

    fake_token = FakeSecret('sometoken')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'owner/repo')

    url = await _call_get_url(dummy, 'owner/repo')
    assert url == 'https://x-token-auth:sometoken@bitbucket.org/owner/repo.git'


@pytest.mark.asyncio
async def test_bitbucket_dc_with_colon_round_052():
    # Bitbucket Data Center uses username:token -> credentials must be percent-encoded
    provider = ProviderType.BITBUCKET_DATA_CENTER
    domains = {provider: 'https://bbdc.example.com/some/path'}

    # include special character to ensure quoting occurs
    fake_token = FakeSecret('User:pa@ss')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'Project/RepoSlug')

    url = await _call_get_url(dummy, 'Project/RepoSlug')

    # Compute expected percent-encoding for username and password
    dc_user, dc_pass = 'User', 'pa@ss'
    expected_creds = f"{_quote(dc_user, safe='')}:{_quote(dc_pass, safe='')}"
    expected_path = 'scm/project/RepoSlug.git'  # project.lower() used for first segment
    assert url == f'https://{expected_creds}@bbdc.example.com/{expected_path}'


@pytest.mark.asyncio
async def test_bitbucket_dc_without_colon_round_052():
    # Bitbucket DC token without colon -> x-token-auth with quoted token
    provider = ProviderType.BITBUCKET_DATA_CENTER
    domains = {provider: 'bbdc.example.com'}

    fake_token = FakeSecret('plain_token')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'Proj/Repo')

    url = await _call_get_url(dummy, 'Proj/Repo')
    expected_creds = f'x-token-auth:{_quote("plain_token", safe="")}'
    expected_path = 'scm/proj/Repo.git'
    assert url == f'https://{expected_creds}@bbdc.example.com/{expected_path}'


@pytest.mark.asyncio
async def test_azure_devops_parts_three_round_052():
    # Azure DevOps with repo_name containing org/project/repo -> long form URL with org username
    provider = ProviderType.AZURE_DEVOPS
    domains = {provider: 'https://dev.azure.com'}

    fake_token = FakeSecret('PAT123')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'OrgName/ProjectName/RepoName')

    url = await _call_get_url(dummy, 'OrgName/ProjectName/RepoName')
    # Expect URL: https://{org}:{token}@{clean_domain}/{org}/{project}/_git/{repo}
    assert url == 'https://OrgName:PAT123@dev.azure.com/OrgName/ProjectName/_git/RepoName'


@pytest.mark.asyncio
async def test_azure_devops_fallback_round_052():
    # Azure DevOps fallback when repo_name doesn't split into 3 parts
    provider = ProviderType.AZURE_DEVOPS
    domains = {provider: 'https://dev.azure.com'}

    fake_token = FakeSecret('FALLBACK')
    provider_tokens = {provider: FakeProviderToken(token=fake_token, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'justrepo')

    url = await _call_get_url(dummy, 'justrepo')
    assert url == 'https://user:FALLBACK@dev.azure.com/justrepo.git'


@pytest.mark.asyncio
async def test_no_token_remote_public_round_052():
    # When token object is falsy (None) -> return public URL without credentials
    provider = ProviderType.GITHUB
    domains = {provider: 'https://github.com'}

    # token is None -> git_token falsy branch
    provider_tokens = {provider: FakeProviderToken(token=None, host=None)}

    dummy = DummySelf(provider_tokens=provider_tokens, provider_domains=domains)
    dummy._repo = FakeRepo(provider, 'owner/repo')

    url = await _call_get_url(dummy, 'owner/repo')
    assert url == 'https://github.com/owner/repo.git'
