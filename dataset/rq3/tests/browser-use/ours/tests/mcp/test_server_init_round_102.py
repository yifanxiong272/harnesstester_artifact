import asyncio
from pathlib import Path

import pytest

from browser_use.mcp import server as server_mod


class DummySelf:
    def __init__(self, config=None):
        # attributes referenced by _init_browser_session
        self.browser_session = None
        self.config = config or {}
        self.tools = None
        self.llm = None
        self.file_system = None
        self._tracked = []

    def _track_session(self, session):
        # record tracked session for assertions
        self._tracked.append(session)


# Fake collaborators to patch into the module under test
class FakeBrowserProfile:
    def __init__(self, **kwargs):
        # keep the constructor arguments for inspection
        self.kwargs = dict(kwargs)


class FakeBrowserSession:
    def __init__(self, browser_profile=None):
        self.browser_profile = browser_profile
        self.started = False

    async def start(self):
        # simulate async startup
        self.started = True


class FakeChatOpenAI:
    def __init__(self, model, api_key, temperature, **kwargs):
        # mirror the expected constructor signature and record params
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.kwargs = dict(kwargs)


class FakeFileSystem:
    def __init__(self, base_dir):
        # store the base_dir for later assertions
        self.base_dir = base_dir


class FakeTools:
    def __init__(self):
        self.created = True


@pytest.fixture(autouse=True)
def ensure_no_external_effects(monkeypatch):
    """Patch noisy or external-facing symbols in the server module."""
    # Prevent real logging configuration changes from affecting tests
    called = {"count": 0}

    def fake_ensure():
        called["count"] += 1

    monkeypatch.setattr(server_mod, "_ensure_all_loggers_use_stderr", fake_ensure)

    # Patch other collaborators with our fakes by default; individual tests may override
    monkeypatch.setattr(server_mod, "BrowserProfile", FakeBrowserProfile)
    monkeypatch.setattr(server_mod, "BrowserSession", FakeBrowserSession)
    monkeypatch.setattr(server_mod, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(server_mod, "FileSystem", FakeFileSystem)
    monkeypatch.setattr(server_mod, "Tools", FakeTools)

    yield called


def test_early_return_round_102(ensure_no_external_effects):
    """If self.browser_session is already set, _init_browser_session returns immediately and
    does not call logger/setup helpers.
    """
    dummy = DummySelf(config={})
    dummy.browser_session = object()  # truthy -> should cause immediate return

    # Call the unbound async method with our dummy self
    coro = server_mod.BrowserUseServer._init_browser_session(dummy, None)
    # run and ensure it completes without modifying our ensure counter
    asyncio.run(coro)

    # ensure_no_external_effects fixture returns the called dict
    # It should remain 0 because early return prevents _ensure_all_loggers_use_stderr from being called
    assert ensure_no_external_effects["count"] == 0
    # browser_session should remain unchanged
    assert dummy.browser_session is not None


def test_full_init_with_allowed_domains_and_kwargs_and_llm_round_102(monkeypatch, ensure_no_external_effects):
    """Test the normal initialization path where:
    - _ensure_all_loggers_use_stderr is invoked
    - profile defaults are merged with get_default_profile
    - allowed_domains override is applied
    - kwargs passed into the method override profile fields
    - BrowserProfile and BrowserSession are constructed and started
    - get_default_llm with base_url and api_key triggers ChatOpenAI construction
    - FileSystem is initialized from profile_config file_system_path
    - _track_session and Tools assignment occur
    """
    # Prepare a dummy self with no active session
    dummy = DummySelf(config={"cfg_key": "cfg_value"})

    # Make sure the module's get_default_profile returns a predictable profile config
    profile_config = {
        "file_system_path": "~/test-browser-use-mcp",
        # include a field that would normally override defaults
        "headless": False,
    }

    monkeypatch.setattr(server_mod, "get_default_profile", lambda cfg: dict(profile_config))

    # Provide an llm config that includes both base_url and api_key to exercise both branches
    llm_config = {"base_url": "http://example.com", "api_key": "test-api-key", "model": "gpt-test", "temperature": 0.3}
    monkeypatch.setattr(server_mod, "get_default_llm", lambda cfg: dict(llm_config))

    # Track whether _ensure_all_loggers_use_stderr is called via the autouse fixture's returned dict
    # ensure_no_external_effects fixture holds the counter (passed in as ensure_no_external_effects)

    allowed = ["example.com", "sub.example.com"]
    extra_kwargs = {"headless": True, "device_scale_factor": 2.0}

    # Run the async initializer
    coro = server_mod.BrowserUseServer._init_browser_session(dummy, allowed, **extra_kwargs)
    asyncio.run(coro)

    # After initialization, _ensure_all_loggers_use_stderr should have been invoked exactly once
    assert ensure_no_external_effects["count"] == 1

    # A BrowserSession instance should have been created and assigned
    assert isinstance(dummy.browser_session, FakeBrowserSession), "browser_session should be FakeBrowserSession"
    assert dummy.browser_session.started is True, "browser_session.start should have been awaited and set started True"

    # The BrowserProfile used to create the session should contain the merged/overridden data
    profile_obj = dummy.browser_session.browser_profile
    assert isinstance(profile_obj, FakeBrowserProfile)
    # allowed_domains must be present and equal to the provided list
    assert profile_obj.kwargs.get("allowed_domains") == allowed
    # kwargs passed into the method should override profile values
    assert profile_obj.kwargs.get("headless") is True
    # also confirm the extra kwarg made it into the profile
    assert profile_obj.kwargs.get("device_scale_factor") == 2.0

    # _track_session should have been invoked with the session
    assert dummy._tracked and dummy._tracked[0] is dummy.browser_session

    # Tools should be constructed and attached
    assert isinstance(dummy.tools, FakeTools)

    # ChatOpenAI should have been constructed and assigned to dummy.llm
    assert isinstance(dummy.llm, FakeChatOpenAI)
    assert dummy.llm.api_key == "test-api-key"
    # base_url should have been forwarded via kwargs into ChatOpenAI
    assert dummy.llm.kwargs.get("base_url") == "http://example.com"

    # FileSystem should have been created from the profile_config file_system_path
    assert isinstance(dummy.file_system, FakeFileSystem)
    expected_path = str(Path(profile_config["file_system_path"]).expanduser())
    assert str(dummy.file_system.base_dir) == expected_path
