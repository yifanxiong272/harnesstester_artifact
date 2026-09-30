import pytest
from types import SimpleNamespace
from pr_agent.git_providers import bitbucket_provider as bbp

# Helper fake PR object used to satisfy __init__ post-PR expectations
def _fake_pr_obj():
    return SimpleNamespace(_BitbucketBase__data={
        "links": {
            "comments": {"href": "http://fake.comments"},
            "self": {"href": "http://fake.self"},
        }
    })

class _DummyCloud:
    def __init__(self, session=None):
        # record that session was passed through, but do nothing else
        self.session = session


def _install_basic_test_monkeypatches(monkeypatch, settings_dict=None, context_get=None, logger=None, set_pr=True):
    """Utility to monkeypatch module-level dependencies in bitbucket_provider."""
    # Replace get_settings to return a simple dict with .get behavior
    monkeypatch.setattr(bbp, "get_settings", lambda: (settings_dict or {}))
    # Replace Cloud with dummy to avoid external network calls
    monkeypatch.setattr(bbp, "Cloud", _DummyCloud)
    # Replace get_logger to supply a controllable fake logger
    if logger is not None:
        monkeypatch.setattr(bbp, "get_logger", lambda: logger)
    # Replace context.get if requested
    if context_get is not None:
        monkeypatch.setattr(bbp.context, "get", context_get)
    # Optionally replace BitbucketProvider.set_pr so __init__ can set a fake pr
    if set_pr:
        def fake_set_pr(self, pr_url):
            self.pr = _fake_pr_obj()
        monkeypatch.setattr(bbp.BitbucketProvider, "set_pr", fake_set_pr)


def test_basic_auth_round_034(monkeypatch):
    """When BITBUCKET.AUTH_TYPE is basic and BASIC_TOKEN present, header should be Basic <token>."""
    fake_logger = SimpleNamespace(exception=lambda *_: None)
    settings = {"BITBUCKET.AUTH_TYPE": "basic", "BITBUCKET.BASIC_TOKEN": "basicval"}
    _install_basic_test_monkeypatches(monkeypatch, settings_dict=settings, context_get=None, logger=fake_logger, set_pr=True)

    prov = bbp.BitbucketProvider(pr_url="some-pr")

    # Authorization header should be set to the BASIC token
    assert prov.headers["Authorization"] == "Basic basicval"
    # bitbucket_comment_api_url should be set from our fake pr object's data
    assert prov.bitbucket_comment_api_url == "http://fake.comments"


def test_bearer_from_context_round_034(monkeypatch):
    """If context.get returns a bearer token, it should be used for Authorization header."""
    fake_logger = SimpleNamespace(exception=lambda *_: None)
    settings = {"BITBUCKET.AUTH_TYPE": "bearer"}
    # context.get should return a token value
    context_get = lambda key, default=None: "ctx-bearer-token"

    _install_basic_test_monkeypatches(monkeypatch, settings_dict=settings, context_get=context_get, logger=fake_logger, set_pr=True)

    prov = bbp.BitbucketProvider(pr_url="pr-with-context")

    assert prov.headers["Authorization"] == "Bearer ctx-bearer-token"
    assert prov.bitbucket_comment_api_url == "http://fake.comments"


def test_bearer_fallback_to_settings_round_034(monkeypatch):
    """If context.get raises, fallback to BITBUCKET.BEARER_TOKEN from settings should be used."""
    # Make context.get raise to exercise the except branch around context.get
    def raising_context_get(key, default=None):
        raise RuntimeError("context failure")

    fake_logger = SimpleNamespace(exception=lambda *_: None)
    settings = {"BITBUCKET.AUTH_TYPE": "bearer", "BITBUCKET.BEARER_TOKEN": "settings-bearer"}

    _install_basic_test_monkeypatches(monkeypatch, settings_dict=settings, context_get=raising_context_get, logger=fake_logger, set_pr=True)

    prov = bbp.BitbucketProvider(pr_url="pr-fallback")

    # Fallback bearer token from settings should be used
    assert prov.headers["Authorization"] == "Bearer settings-bearer"
    assert prov.bitbucket_comment_api_url == "http://fake.comments"


def test_missing_token_raises_and_logs_round_034(monkeypatch):
    """If auth_type is basic but BASIC_TOKEN is missing, __init__ should log and re-raise the ValueError."""
    # Provide no BASIC_TOKEN to force get_token to raise
    fake_logger = SimpleNamespace()
    fake_logger.called = False

    def fake_exception(msg):
        # record that exception() was invoked with a message containing the expected substring
        fake_logger.called = True
        fake_logger.last_msg = msg

    fake_logger.exception = fake_exception

    settings = {"BITBUCKET.AUTH_TYPE": "basic"}  # note: no BASIC_TOKEN key
    # We don't need set_pr because the failure happens before set_pr would be called
    _install_basic_test_monkeypatches(monkeypatch, settings_dict=settings, context_get=None, logger=fake_logger, set_pr=False)

    with pytest.raises(ValueError):
        bbp.BitbucketProvider(pr_url="will-not-get-this-far")

    # Ensure logger.exception was called during the handled exception path in __init__
    assert fake_logger.called is True
    assert "Failed to initialize Bitbucket authentication" in fake_logger.last_msg


def test_pr_url_none_logs_and_raises_round_034(monkeypatch):
    """If pr_url is falsy, attribute access on self.pr will raise. Verify exception type and message."""
    fake_logger = SimpleNamespace()

    def fake_exception(msg):
        # If invoked, record it, but we do not require it to be called for this scenario
        fake_logger.called = True
        fake_logger.last_msg = msg

    fake_logger.called = False
    fake_logger.exception = fake_exception

    # Provide valid bearer token so no earlier exception occurs
    settings = {"BITBUCKET.AUTH_TYPE": "bearer", "BITBUCKET.BEARER_TOKEN": "present-token"}
    # context.get returns None but get_token fallback will pick up the present token
    context_get = lambda key, default=None: None

    # Do not install set_pr so that self.pr remains None and later attribute access fails
    _install_basic_test_monkeypatches(monkeypatch, settings_dict=settings, context_get=context_get, logger=fake_logger, set_pr=False)

    with pytest.raises(AttributeError) as ei:
        bbp.BitbucketProvider(pr_url=None)

    # The AttributeError should indicate that NoneType has no attribute '_BitbucketBase__data'
    assert "_BitbucketBase__data" in str(ei.value)
