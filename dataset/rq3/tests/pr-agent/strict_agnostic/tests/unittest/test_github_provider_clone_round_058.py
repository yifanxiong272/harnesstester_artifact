import types
import pytest
from types import SimpleNamespace

from pr_agent.git_providers.github_provider import GithubProvider


def make_provider(token, base_url_html, deployment_type="default"):
    """Create a GithubProvider instance without running __init__ and set the
    minimal attributes needed by _prepare_clone_url_with_token.
    """
    provider = object.__new__(GithubProvider)
    provider.auth = SimpleNamespace(token=token)
    provider.base_url_html = base_url_html
    provider.deployment_type = deployment_type
    return provider


def test_missing_token_and_missing_base_url_round_058():
    # missing token should return None
    prov1 = make_provider(token=None, base_url_html="https://github.com")
    assert prov1._prepare_clone_url_with_token("https://github.com/org/repo.git") is None

    # missing base_url_html should return None
    prov2 = make_provider(token="token123", base_url_html=None)
    assert prov2._prepare_clone_url_with_token("https://github.com/org/repo.git") is None


def test_base_url_missing_scheme_round_058():
    # base_url does not contain required scheme 'https://' -> None
    prov = make_provider(token="t", base_url_html="http://github.com")
    assert prov._prepare_clone_url_with_token("https://github.com/org/repo.git") is None


def test_empty_github_com_round_058():
    # base_url_html is exactly the scheme leaving github_com empty -> None
    prov = make_provider(token="t", base_url_html="https://")
    assert prov._prepare_clone_url_with_token("https://github.com/org/repo.git") is None


def test_repo_url_does_not_contain_github_com_round_058():
    # repo url doesn't contain the derived github_com -> None
    prov = make_provider(token="t", base_url_html="https://github.com")
    bad_repo = "https://gitlab.com/org/repo.git"
    assert prov._prepare_clone_url_with_token(bad_repo) is None


def test_repo_full_name_empty_round_058():
    # repo_url_to_clone ends exactly at github_com -> repo_full_name empty -> None
    prov = make_provider(token="t", base_url_html="https://github.com")
    repo_exact = "https://github.com"
    assert prov._prepare_clone_url_with_token(repo_exact) is None


def test_successful_clone_url_with_and_without_app_deployment_round_058():
    # normal deployment_type -> no 'git:' prefix
    token = "mytoken"
    base = "https://github.com"
    repo = "https://github.com/Codium-ai/pr-agent-pro.git"
    prov = make_provider(token=token, base_url_html=base, deployment_type="default")
    expected = f"https://{token}@github.com/Codium-ai/pr-agent-pro.git"
    assert prov._prepare_clone_url_with_token(repo) == expected

    # app deployment_type -> includes 'git:' after scheme
    prov_app = make_provider(token=token, base_url_html=base, deployment_type="app")
    expected_app = f"https://git:{token}@github.com/Codium-ai/pr-agent-pro.git"
    assert prov_app._prepare_clone_url_with_token(repo) == expected_app
