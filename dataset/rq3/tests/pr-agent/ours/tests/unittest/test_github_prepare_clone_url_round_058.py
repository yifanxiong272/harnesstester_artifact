import pytest

from pr_agent.git_providers.github_provider import GithubProvider


class _LoggerStub:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # store exact message for assertion
        self.errors.append(msg)


class _Auth:
    def __init__(self, token):
        self.token = token


class _FakeSelf:
    def __init__(self, token, base_url_html, deployment_type="oauth"):
        self.auth = _Auth(token)
        self.base_url_html = base_url_html
        self.deployment_type = deployment_type


@pytest.fixture(autouse=True)
def patch_logger(monkeypatch):
    """Patch the get_logger symbol in the module so tests can assert logged errors.

    This follows the contract to patch the symbol where the code under test resolves it.
    """
    logger = _LoggerStub()

    # patch the module-level get_logger used by the function under test
    monkeypatch.setattr(
        "pr_agent.git_providers.github_provider.get_logger", lambda: logger
    )
    return logger


def test_missing_token_or_base_round_058(patch_logger):
    fake = _FakeSelf(token=None, base_url_html=None)
    res = GithubProvider._prepare_clone_url_with_token(fake, "https://github.com/owner/repo.git")
    assert res is None
    # exact message emitted by the function when token or base missing
    assert patch_logger.errors[-1] == "Either missing auth token or missing base url"


def test_missing_scheme_round_058(patch_logger):
    # base url missing the required scheme 'https://'
    fake = _FakeSelf(token="T", base_url_html="http://github.com")
    res = GithubProvider._prepare_clone_url_with_token(fake, "https://github.com/owner/repo.git")
    assert res is None
    assert patch_logger.errors[-1] == "Base url: http://github.com is missing prefix: https://"


def test_empty_github_com_round_058(patch_logger):
    # base url exactly the scheme results in empty github_com after split
    fake = _FakeSelf(token="T", base_url_html="https://")
    res = GithubProvider._prepare_clone_url_with_token(fake, "https://github.com/owner/repo.git")
    assert res is None
    assert patch_logger.errors[-1] == "Base url: https:// has an empty base url"


def test_github_com_not_in_repo_round_058(patch_logger):
    fake = _FakeSelf(token="T", base_url_html="https://github.com")
    # repo url does not contain the github base host portion
    repo_url = "https://notgithub.example/owner/repo.git"
    res = GithubProvider._prepare_clone_url_with_token(fake, repo_url)
    assert res is None
    assert patch_logger.errors[-1] == f"url to clone: {repo_url} does not contain github.com"


def test_repo_full_name_empty_round_058(patch_logger):
    fake = _FakeSelf(token="T", base_url_html="https://github.com")
    # repo url that ends exactly with the host yields empty repo_full_name
    repo_url = "https://github.com"
    res = GithubProvider._prepare_clone_url_with_token(fake, repo_url)
    assert res is None
    assert patch_logger.errors[-1] == f"url to clone: {repo_url} is malformed"


def test_success_app_deployment_round_058():
    fake = _FakeSelf(token="TOKEN123", base_url_html="https://github.com", deployment_type="app")
    repo_url = "https://github.com/owner/repo.git"
    res = GithubProvider._prepare_clone_url_with_token(fake, repo_url)
    # when deployment_type == 'app' the function inserts 'git:' after the scheme
    assert res == "https://git:TOKEN123@github.com/owner/repo.git"


def test_success_non_app_round_058():
    fake = _FakeSelf(token="TOKEN456", base_url_html="https://github.com", deployment_type="oauth")
    repo_url = "https://github.com/owner/repo.git"
    res = GithubProvider._prepare_clone_url_with_token(fake, repo_url)
    # non-'app' deployment does not include 'git:'
    assert res == "https://TOKEN456@github.com/owner/repo.git"
