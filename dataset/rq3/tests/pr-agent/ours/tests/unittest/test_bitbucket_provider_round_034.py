import pytest
from types import SimpleNamespace

import pr_agent.git_providers.bitbucket_provider as bb_mod
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider


class FakeSession:
    def __init__(self):
        self.headers = {"Content-Type": "application/json"}


class FakeCloud:
    def __init__(self, session):
        # record the session passed in for assertions
        self.session = session


class FakeLogger:
    def __init__(self):
        self.messages = []

    def exception(self, msg):
        # store the message for inspection
        self.messages.append(msg)


class FakePR:
    def __init__(self):
        self._BitbucketBase__data = {
            "links": {
                "comments": {"href": "http://fake/comments"},
                "self": {"href": "http://fake/self"},
            }
        }


def _patch_common(monkeypatch, get_settings_return=None, context_obj=None, logger_obj=None):
    # Patch requests.Session used by the module
    monkeypatch.setattr(bb_mod.requests, "Session", lambda: FakeSession())
    # Patch the Cloud client to avoid network
    monkeypatch.setattr(bb_mod, "Cloud", FakeCloud)
    # Patch get_settings to return a mapping-like object
    if get_settings_return is None:
        get_settings_return = {}
    monkeypatch.setattr(bb_mod, "get_settings", lambda: get_settings_return)
    # Patch context (starlette_context.context)
    if context_obj is not None:
        monkeypatch.setattr(bb_mod, "context", context_obj)
    # Patch get_logger to return our fake logger
    if logger_obj is None:
        logger_obj = FakeLogger()
    monkeypatch.setattr(bb_mod, "get_logger", lambda: logger_obj)
    return logger_obj


def test_init_basic_round_034(monkeypatch):
    """When BITBUCKET.AUTH_TYPE is basic and BITBUCKET.BASIC_TOKEN exists, init sets Basic header and URLs."""
    # prepare settings to trigger basic auth
    settings = {"BITBUCKET.AUTH_TYPE": "basic", "BITBUCKET.BASIC_TOKEN": "basic_xyz"}
    logger = _patch_common(monkeypatch, get_settings_return=settings)

    # Avoid network in set_pr: ensure set_pr sets self.pr to a fake object with expected structure
    def fake_set_pr(self, pr_url):
        self.pr = FakePR()

    monkeypatch.setattr(BitbucketProvider, "set_pr", fake_set_pr)

    provider = BitbucketProvider(pr_url="http://fake/pr", incremental=False)

    # Authorization header must be set to Basic <token>
    assert provider.headers["Authorization"] == "Basic basic_xyz"
    # bitbucket_client must be our FakeCloud constructed with the session
    assert isinstance(provider.bitbucket_client, FakeCloud)
    # verify URLs were pulled from the fake PR structure
    assert provider.bitbucket_comment_api_url == "http://fake/comments"
    assert provider.bitbucket_pull_request_api_url == "http://fake/self"
    # ensure no exception was logged
    assert logger.messages == []


def test_init_bearer_from_context_round_034(monkeypatch):
    """When auth_type is bearer and context provides bitbucket_bearer_token, header uses context token."""
    # get_settings returns empty mapping -> default auth_type should be 'bearer'
    context_obj = SimpleNamespace(get=lambda k, d=None: "ctx_token_value")
    logger = _patch_common(monkeypatch, get_settings_return={}, context_obj=context_obj)

    # patch set_pr to avoid external calls
    monkeypatch.setattr(BitbucketProvider, "set_pr", lambda self, pr_url: setattr(self, "pr", FakePR()))

    provider = BitbucketProvider(pr_url="http://fake/pr2")

    # Should prefer context token and set Bearer header
    assert provider.headers["Authorization"] == "Bearer ctx_token_value"
    # client created with FakeCloud
    assert isinstance(provider.bitbucket_client, FakeCloud)
    # no logged exceptions
    assert logger.messages == []


def test_init_bearer_fallback_to_settings_round_034(monkeypatch):
    """If context.get raises, __init__ falls back to BITBUCKET.BEARER_TOKEN from settings."""
    # context.get will raise to exercise except: branch inside bearer handling
    def raising_get(k, d=None):
        raise RuntimeError("context failure")

    context_obj = SimpleNamespace(get=raising_get)
    settings = {"BITBUCKET.BEARER_TOKEN": "bearer_from_settings"}
    logger = _patch_common(monkeypatch, get_settings_return=settings, context_obj=context_obj)

    monkeypatch.setattr(BitbucketProvider, "set_pr", lambda self, pr_url: setattr(self, "pr", FakePR()))

    provider = BitbucketProvider(pr_url="http://fake/pr3")

    # Should use bearer token from settings after context.get failed
    assert provider.headers["Authorization"] == "Bearer bearer_from_settings"
    assert isinstance(provider.bitbucket_client, FakeCloud)
    assert logger.messages == []


def test_init_missing_token_logs_and_raises_round_034(monkeypatch):
    """If required token is missing (e.g., basic token absent), __init__ logs and re-raises the error."""
    # Provide basic auth type but omit BASIC_TOKEN to trigger get_token raising ValueError
    settings = {"BITBUCKET.AUTH_TYPE": "basic"}
    fake_logger = _patch_common(monkeypatch, get_settings_return=settings, logger_obj=FakeLogger())

    # patch set_pr to a no-op in case it's reached (it should not be reached because init will fail)
    monkeypatch.setattr(BitbucketProvider, "set_pr", lambda self, pr_url: setattr(self, "pr", FakePR()))

    with pytest.raises(ValueError) as excinfo:
        BitbucketProvider(pr_url=None)

    # The outer except should have logged the exception message
    assert any("Failed to initialize Bitbucket authentication" in m for m in fake_logger.messages)
    # The raised ValueError should mention Basic auth requires a token (origin message)
    assert "Basic auth requires a token" in str(excinfo.value)


def test_init_unsupported_auth_type_raises_round_034(monkeypatch):
    """An unsupported BITBUCKET.AUTH_TYPE should cause initialization to log and raise ValueError."""
    settings = {"BITBUCKET.AUTH_TYPE": "weird_auth"}
    fake_logger = _patch_common(monkeypatch, get_settings_return=settings, logger_obj=FakeLogger())

    with pytest.raises(ValueError) as excinfo:
        # No pr_url needed; init should fail before Cloud construction
        BitbucketProvider(pr_url=None)

    # Confirm the error message mentions the unsupported type
    assert "Unsupported auth_type: weird_auth" in str(excinfo.value)
    # Confirm the exception was logged by get_logger().exception
    assert any("Failed to initialize Bitbucket authentication" in m for m in fake_logger.messages)
