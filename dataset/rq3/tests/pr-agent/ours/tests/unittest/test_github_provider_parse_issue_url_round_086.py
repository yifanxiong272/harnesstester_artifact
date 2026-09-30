import sys
import types
import pytest

# Inject lightweight dummy modules to satisfy top-level imports in the target module
# without pulling in real external dependencies or network access.
github_mod = types.ModuleType("github")
github_issue_mod = types.ModuleType("github.Issue")
setattr(github_issue_mod, "Issue", object)
setattr(github_mod, "Issue", object)
setattr(github_mod, "AppAuthentication", object)
setattr(github_mod, "Auth", object)
setattr(github_mod, "Github", object)
setattr(github_mod, "GithubException", Exception)
sys.modules["github"] = github_mod
sys.modules["github.Issue"] = github_issue_mod

retry_mod = types.ModuleType("retry")
# simple pass-through decorator to satisfy `from retry import retry`
def _dummy_retry(fn=None, *dargs, **dkwargs):
    if fn is None:
        return lambda f: f
    return fn
retry_mod.retry = _dummy_retry
sys.modules["retry"] = retry_mod

starlette_ctx = types.ModuleType("starlette_context")
setattr(starlette_ctx, "context", {})
sys.modules["starlette_context"] = starlette_ctx

# Now import the class under test
from pr_agent.git_providers.github_provider import GithubProvider


def _make_provider():
    # Avoid running GithubProvider.__init__ which may require real config or network.
    return GithubProvider.__new__(GithubProvider)


def test_parse_issue_url_api_v3_prefix_success_round_086():
    provider = _make_provider()
    # path starts with /api/v3 and netloc contains api.github.com -> triggers the api branch
    url = "https://api.github.com/api/v3/repos/owner/repo/issues/123"
    repo, num = provider._parse_issue_url(url)
    assert repo == "owner/repo"
    assert isinstance(num, int) and num == 123


def test_parse_issue_url_api_branch_bad_structure_round_086():
    provider = _make_provider()
    # api.github.com netloc but wrong segment (not 'issues') -> should raise the ISSUE URL error
    url = "https://api.github.com/repos/owner/repo/notissues/123"
    with pytest.raises(ValueError) as ei:
        provider._parse_issue_url(url)
    assert "The provided URL does not appear to be a GitHub ISSUE URL" in str(ei.value)


def test_parse_issue_url_api_branch_non_int_issue_round_086():
    provider = _make_provider()
    # issue number not an integer -> should raise conversion error with expected message
    url = "https://api.github.com/repos/owner/repo/issues/abc"
    with pytest.raises(ValueError) as ei:
        provider._parse_issue_url(url)
    assert "Unable to convert issue number to integer" in str(ei.value)


def test_parse_issue_url_non_api_success_round_086():
    provider = _make_provider()
    # normal github.com URL (non-api) -> returns repo and number from alternative branch
    url = "https://github.com/owner/repo/issues/45"
    repo, num = provider._parse_issue_url(url)
    assert repo == "owner/repo"
    assert num == 45


def test_parse_issue_url_non_api_bad_structure_round_086():
    provider = _make_provider()
    # non-api host and wrong path segment at the PR branch -> should raise PR issue error
    url = "https://github.com/owner/repo/pulls/45"
    with pytest.raises(ValueError) as ei:
        provider._parse_issue_url(url)
    assert "The provided URL does not appear to be a GitHub PR issue" in str(ei.value)


def test_parse_issue_url_non_api_non_int_round_086():
    provider = _make_provider()
    # non-api branch but issue number not integer -> conversion error
    url = "https://github.com/owner/repo/issues/NaN"
    with pytest.raises(ValueError) as ei:
        provider._parse_issue_url(url)
    assert "Unable to convert issue number to integer" in str(ei.value)
