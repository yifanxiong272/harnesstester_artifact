# file: pr_agent/git_providers/github_provider.py:1193-1225
# asked: {"lines": [1194, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1219, 1221, 1222, 1223, 1224, 1225], "branches": [[1203, 1204], [1203, 1206], [1206, 1207], [1206, 1209], [1210, 1211], [1210, 1213], [1213, 1214], [1213, 1216], [1217, 1218], [1217, 1221], [1222, 1223], [1222, 1224]]}
# gained: {"lines": [1194, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1219, 1221, 1222, 1223, 1224, 1225], "branches": [[1203, 1204], [1203, 1206], [1206, 1207], [1206, 1209], [1210, 1211], [1210, 1213], [1213, 1214], [1213, 1216], [1217, 1218], [1217, 1221], [1222, 1223], [1222, 1224]]}

import types
import pytest

from pr_agent.git_providers import github_provider as gp_mod
from pr_agent.git_providers.github_provider import GithubProvider


class LoggerStub:
    def __init__(self):
        self.errors = []

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


def make_instance_without_init():
    # Create instance without running __init__
    inst = object.__new__(GithubProvider)
    return inst


def setup_logger_stub(monkeypatch):
    logger = LoggerStub()
    # gp_mod.get_logger is the function imported in the module; patch it to return our stub
    monkeypatch.setattr(gp_mod, "get_logger", lambda: logger)
    return logger


def make_auth(token):
    return types.SimpleNamespace(token=token)


def call_prepare(inst, repo_url):
    # call the protected method
    return inst._prepare_clone_url_with_token(repo_url)


def test_prepare_clone_missing_token_or_baseurl(monkeypatch):
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    # Case: missing token
    inst.auth = make_auth(None)
    inst.base_url_html = "https://github.com"
    inst.deployment_type = None

    res = call_prepare(inst, "https://github.com/org/repo.git")
    assert res is None
    assert logger.errors, "Expected an error logged for missing token"
    assert "Either missing auth token or missing base url" in logger.errors[0][0][0]

    # Reset and test missing base_url
    logger.errors.clear()
    inst.auth = make_auth("sometoken")
    inst.base_url_html = None

    res = call_prepare(inst, "https://github.com/org/repo.git")
    assert res is None
    assert logger.errors, "Expected an error logged for missing base url"
    assert "Either missing auth token or missing base url" in logger.errors[0][0][0]


def test_prepare_clone_missing_scheme(monkeypatch):
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    inst.auth = make_auth("token123")
    # base_url without https:// should trigger the scheme error
    inst.base_url_html = "github.enterprise.com"
    inst.deployment_type = None

    res = call_prepare(inst, "https://github.enterprise.com/org/repo.git")
    assert res is None
    assert logger.errors, "Expected an error logged for missing scheme"
    assert f"missing prefix: https://" in logger.errors[0][0][0]


def test_prepare_clone_empty_github_com(monkeypatch):
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    inst.auth = make_auth("token123")
    # base_url_html that results in empty github_com when split by scheme
    inst.base_url_html = "https://"
    inst.deployment_type = None

    res = call_prepare(inst, "https://whatever/org/repo.git")
    assert res is None
    assert logger.errors, "Expected an error logged for empty base url"
    assert "has an empty base url" in logger.errors[0][0][0]


def test_prepare_clone_github_com_not_in_repo_url(monkeypatch):
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    inst.auth = make_auth("tokenABC")
    inst.base_url_html = "https://github.enterprise.com"
    inst.deployment_type = None

    # repo url points to github.com not github.enterprise.com
    res = call_prepare(inst, "https://github.com/org/repo.git")
    assert res is None
    assert logger.errors, "Expected an error when github_com is not in repo url"
    assert "does not contain" in logger.errors[0][0][0]


def test_prepare_clone_repo_full_name_malformed(monkeypatch):
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    inst.auth = make_auth("tokenXYZ")
    inst.base_url_html = "https://github.com"
    inst.deployment_type = None

    # repo_url_to_clone exactly equals base host -> repo_full_name becomes empty
    res = call_prepare(inst, "https://github.com")
    assert res is None
    assert logger.errors, "Expected an error for malformed repo url"
    assert "is malformed" in logger.errors[0][0][0]


def test_prepare_clone_success_and_app_deployment(monkeypatch):
    # successful non-app deployment
    logger = setup_logger_stub(monkeypatch)

    inst = make_instance_without_init()
    inst.auth = make_auth("tok123")
    inst.base_url_html = "https://github.com"
    inst.deployment_type = "server"  # not 'app'

    repo_url = "https://github.com/Codium-ai/pr-agent-pro.git"
    res = call_prepare(inst, repo_url)
    assert res == "https://tok123@github.com/Codium-ai/pr-agent-pro.git"
    # no error logged
    assert logger.errors == []

    # successful app deployment adds 'git:' after scheme
    inst.deployment_type = "app"
    res_app = call_prepare(inst, repo_url)
    assert res_app == "https://git:tok123@github.com/Codium-ai/pr-agent-pro.git"
    assert logger.errors == []
