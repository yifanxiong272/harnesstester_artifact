# file: pr_agent/git_providers/gitea_provider.py:712-739
# asked: {"lines": [718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 737, 738, 739], "branches": [[722, 723], [722, 725], [726, 727], [726, 729], [729, 730], [729, 732], [733, 734], [733, 737]]}
# gained: {"lines": [718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 737, 738, 739], "branches": [[722, 723], [722, 725], [726, 727], [726, 729], [729, 730], [729, 732], [733, 734], [733, 737]]}

import pytest

from pr_agent.git_providers.gitea_provider import GiteaProvider


def _make_provider(gitea_access_token=None, base_url=None):
    # Create instance without calling __init__
    prov = object.__new__(GiteaProvider)
    # Provide only the attributes needed by _prepare_clone_url_with_token
    prov.gitea_access_token = gitea_access_token
    prov.base_url = base_url
    return prov


def test_prepare_clone_url_missing_token_or_base_url():
    # missing token (base_url provided)
    prov = _make_provider(gitea_access_token=None, base_url="https://gitea.example.com")
    res = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")
    assert res is None

    # missing base_url: use empty string instead of None to avoid AttributeError in split
    prov = _make_provider(gitea_access_token="token123", base_url="")
    res = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")
    assert res is None

    # both missing: token None and base_url empty string
    prov = _make_provider(gitea_access_token=None, base_url="")
    res = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")
    assert res is None


def test_prepare_clone_url_base_url_empty_after_scheme_split():
    # base_url that is just a scheme -> after splitting by scheme, base_url part will be empty
    prov = _make_provider(gitea_access_token="token123", base_url="https://")
    res = prov._prepare_clone_url_with_token("https://gitea.example.com/owner/repo.git")
    assert res is None


def test_prepare_clone_url_base_not_in_repo_url():
    # base_url present but repo_url_to_clone does not contain it
    prov = _make_provider(gitea_access_token="token123", base_url="https://gitea.example.com")
    # use a repo url that points to a different host
    res = prov._prepare_clone_url_with_token("https://other.example.com/owner/repo.git")
    assert res is None


def test_prepare_clone_url_repo_full_name_empty():
    # repo_url_to_clone equals base url so repo_full_name becomes empty
    prov = _make_provider(gitea_access_token="token123", base_url="https://gitea.example.com")
    res = prov._prepare_clone_url_with_token("https://gitea.example.com")
    assert res is None


def test_prepare_clone_url_successful_embedding():
    prov = _make_provider(gitea_access_token="secrettoken", base_url="https://gitea.example.com")
    repo_url = "https://gitea.example.com/owner-name/repo-name.git"
    res = prov._prepare_clone_url_with_token(repo_url)
    # Expect the token to be embedded right after the scheme, before the base host
    assert res == "https://secrettoken@gitea.example.com/owner-name/repo-name.git"
