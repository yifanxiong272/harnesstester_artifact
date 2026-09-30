# file: pr_agent/git_providers/bitbucket_provider.py:28-78
# asked: {"lines": [31, 32, 34, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78], "branches": [[39, 40], [39, 41], [43, 44], [43, 46], [46, 47], [46, 56], [52, 53], [52, 54], [75, 76], [75, 77]]}
# gained: {"lines": [31, 32, 34, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 52, 53, 54, 56, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78], "branches": [[39, 40], [39, 41], [43, 44], [43, 46], [46, 47], [46, 56], [52, 53], [52, 54], [75, 76]]}

import types
from types import SimpleNamespace
import pytest

import pr_agent.git_providers.bitbucket_provider as bb_module
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider


class FakeSettings:
    def __init__(self, mapping):
        self._mapping = mapping or {}

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class FakeLogger:
    def __init__(self):
        self.last_exception = None
        self.called = False

    def exception(self, msg):
        self.called = True
        self.last_exception = msg


class FakeContext:
    def __init__(self, to_return=None, raise_exc=False):
        self.to_return = to_return
        self.raise_exc = raise_exc
        self.calls = []

    def get(self, key, default=None):
        self.calls.append((key, default))
        if self.raise_exc:
            raise RuntimeError("context failure")
        return self.to_return


def _fake_set_pr_factory(comment_url="comments_url", self_url="self_url"):
    def fake_set_pr(self, pr_url):
        ns = SimpleNamespace()
        setattr(ns, "_BitbucketBase__data", {"links": {"comments": {"href": comment_url}, "self": {"href": self_url}}})
        self.pr = ns
    return fake_set_pr


def _patch_cloud(monkeypatch):
    # Patch Cloud to a simple callable that records session argument
    def fake_cloud(session=None):
        return SimpleNamespace(_session=session)
    monkeypatch.setattr(bb_module, "Cloud", fake_cloud)


def _patch_get_logger(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(bb_module, "get_logger", lambda: fake_logger)
    return fake_logger


def _patch_get_settings(monkeypatch, mapping):
    monkeypatch.setattr(bb_module, "get_settings", lambda: FakeSettings(mapping))


def _patch_context(monkeypatch, to_return=None, raise_exc=False):
    fake_context = FakeContext(to_return=to_return, raise_exc=raise_exc)
    monkeypatch.setattr(bb_module, "context", fake_context)
    return fake_context


def _patch_set_pr(monkeypatch, comment_url="comments_url", self_url="self_url"):
    monkeypatch.setattr(BitbucketProvider, "set_pr", _fake_set_pr_factory(comment_url, self_url))


def test_bearer_auth_uses_context_token_and_sets_urls(monkeypatch):
    # Prepare settings to default to bearer (no explicit value needed)
    _patch_get_settings(monkeypatch, {"BITBUCKET.AUTH_TYPE": "bearer"})
    fake_context = _patch_context(monkeypatch, to_return="CTX_TOKEN", raise_exc=False)
    _patch_cloud(monkeypatch)
    _patch_set_pr(monkeypatch, comment_url="http://comments", self_url="http://self")

    provider = BitbucketProvider(pr_url="some_url")

    # Authorization header should come from context token
    assert provider.headers["Content-Type"] == "application/json"
    assert provider.headers["Authorization"] == "Bearer CTX_TOKEN"
    # URLs pulled from pr set by fake set_pr
    assert provider.bitbucket_comment_api_url == "http://comments"
    assert provider.bitbucket_pull_request_api_url == "http://self"
    # ensure cloud session present
    assert hasattr(provider.bitbucket_client, "_session")
    # ensure context.get was called for bearer token
    assert ("bitbucket_bearer_token", None) in fake_context.calls


def test_basic_auth_uses_settings_token(monkeypatch):
    # Prepare settings to specify basic auth and provide basic token
    _patch_get_settings(monkeypatch, {"BITBUCKET.AUTH_TYPE": "basic", "BITBUCKET.BASIC_TOKEN": "BASIC123"})
    _patch_cloud(monkeypatch)
    _patch_set_pr(monkeypatch, comment_url="c2", self_url="s2")

    provider = BitbucketProvider(pr_url="u2")

    assert provider.headers["Content-Type"] == "application/json"
    assert provider.headers["Authorization"] == "Basic BASIC123"
    assert provider.bitbucket_comment_api_url == "c2"
    assert provider.bitbucket_pull_request_api_url == "s2"


def test_bearer_context_exception_falls_back_to_settings(monkeypatch):
    # Context.get will raise; get_settings provides BEARER token
    _patch_get_settings(monkeypatch, {"BITBUCKET.AUTH_TYPE": "bearer", "BITBUCKET.BEARER_TOKEN": "SET_TOKEN"})
    _patch_context(monkeypatch, to_return=None, raise_exc=True)
    _patch_cloud(monkeypatch)
    _patch_set_pr(monkeypatch, comment_url="cc", self_url="ss")

    provider = BitbucketProvider(pr_url="u3")

    # Because context.get raised, provider should use settings token
    assert provider.headers["Authorization"] == "Bearer SET_TOKEN"
    assert provider.bitbucket_comment_api_url == "cc"
    assert provider.bitbucket_pull_request_api_url == "ss"


def test_unsupported_auth_type_logs_and_raises(monkeypatch):
    # Unsupported auth type should cause ValueError and logger.exception to be called
    _patch_get_settings(monkeypatch, {"BITBUCKET.AUTH_TYPE": "unsupported"})
    fake_logger = _patch_get_logger(monkeypatch)
    # Cloud should not be called; but patch anyway to be safe
    _patch_cloud(monkeypatch)

    with pytest.raises(ValueError) as excinfo:
        BitbucketProvider(pr_url=None)

    assert "Unsupported auth_type" in str(excinfo.value)
    assert fake_logger.called is True
    assert "Unsupported auth_type" in (fake_logger.last_exception or "")


def test_missing_token_for_basic_logs_and_raises(monkeypatch):
    # BASIC auth but missing token should raise and be logged
    _patch_get_settings(monkeypatch, {"BITBUCKET.AUTH_TYPE": "basic"})  # no BASIC_TOKEN provided
    fake_logger = _patch_get_logger(monkeypatch)
    _patch_cloud(monkeypatch)

    with pytest.raises(ValueError) as excinfo:
        BitbucketProvider(pr_url=None)

    # Ensure the error mentions Basic auth requires a token
    assert "Basic auth requires a token" in str(excinfo.value)
    assert fake_logger.called is True
    assert "Failed to initialize Bitbucket authentication" in (fake_logger.last_exception or "")
