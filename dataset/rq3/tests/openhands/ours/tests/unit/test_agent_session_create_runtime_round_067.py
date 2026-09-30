import asyncio
from types import SimpleNamespace
import pytest

import openhands.server.session.agent_session as agent_session
from openhands.core.exceptions import AgentRuntimeUnavailableError


class FakeRemoteRuntime:
    def __init__(self, **kwargs):
        # store what was passed so tests can assert
        self._init_kwargs = kwargs
        self.plugins = kwargs.get("plugins", [])
        self.maybe_run_setup_script_called = False
        self.maybe_setup_git_hooks_called = False

    async def connect(self):
        # succeed by default
        self.connected = True

    async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
        self.clone_args = (git_provider_tokens, selected_repository, selected_branch)

    def maybe_run_setup_script(self):
        self.maybe_run_setup_script_called = True

    def maybe_setup_git_hooks(self):
        self.maybe_setup_git_hooks_called = True


class FakeLocalRuntime:
    def __init__(self, **kwargs):
        self._init_kwargs = kwargs
        self.plugins = kwargs.get("plugins", [])
        self.maybe_run_setup_script_called = False
        self.maybe_setup_git_hooks_called = False

    async def connect(self):
        # default to success unless overridden in test via attribute
        if getattr(self, "_raise_on_connect", False):
            raise AgentRuntimeUnavailableError("simulated-failure")
        self.connected = True

    async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
        self.clone_args = (git_provider_tokens, selected_repository, selected_branch)

    def maybe_run_setup_script(self):
        self.maybe_run_setup_script_called = True

    def maybe_setup_git_hooks(self):
        self.maybe_setup_git_hooks_called = True


class FakeSecrets:
    def __init__(self, custom_secrets=None):
        self.custom = custom_secrets or {}

    def get_env_vars(self):
        # return a shallow copy to mimic real behavior
        return dict(self.custom)


class FakeProviderHandler:
    def __init__(self, provider_tokens=None):
        self.provider_tokens = provider_tokens

    async def get_env_vars(self, expose_secrets=False):
        # Expose some provider-derived env var
        return {"GIT_PROVIDER_KEY": "git-val"}


async def _call_call_sync_from_async(func):
    # simplified replacement for call_sync_from_async used in the module
    if asyncio.iscoroutinefunction(func):
        return await func()
    # call synchronous function directly
    return func()


def make_dummy_session():
    # Create a minimal dummy 'self' object with the attributes _create_runtime expects
    calls = {}

    def override_provider_tokens_with_custom_secret(git_provider_tokens, custom_secrets):
        calls["override_called_with"] = (git_provider_tokens, custom_secrets)
        # prioritize custom secret provider token if present
        if custom_secrets and isinstance(custom_secrets, dict) and custom_secrets.get("provider"):
            return {"provider": custom_secrets["provider"]}
        return git_provider_tokens

    dummy = SimpleNamespace()
    dummy.runtime = None
    # small logger stub
    dummy.logger = SimpleNamespace(debug=lambda *a, **k: None, error=lambda *a, **k: None)
    dummy.event_stream = object()
    dummy.llm_registry = object()
    dummy.sid = "SOME-SID"
    dummy._status_callback = None
    dummy.user_id = "user-123"
    dummy.override_provider_tokens_with_custom_secret = override_provider_tokens_with_custom_secret
    calls_holder = calls
    dummy._calls = calls_holder
    return dummy


def patch_module_for_tests(monkeypatch, *, remote_runtime_cls=FakeRemoteRuntime, provider_handler_cls=FakeProviderHandler, secrets_cls=FakeSecrets):
    # Patch module-level factories and helpers with our fakes
    monkeypatch.setattr(agent_session, "get_runtime_cls", lambda name: remote_runtime_cls)
    # Ensure RemoteRuntime equality check can succeed if needed
    monkeypatch.setattr(agent_session, "RemoteRuntime", remote_runtime_cls)
    monkeypatch.setattr(agent_session, "ProviderHandler", provider_handler_cls)
    monkeypatch.setattr(agent_session, "Secrets", secrets_cls)
    monkeypatch.setattr(agent_session, "call_sync_from_async", lambda f: _call_call_sync_from_async(f))


def run_create_runtime(dummy_self, runtime_name, config, agent, git_provider_tokens=None, custom_secrets=None, selected_repository=None, selected_branch=None):
    # helper to call the async create_runtime synchronously in tests
    coro = agent_session.AgentSession._create_runtime(
        dummy_self,
        runtime_name,
        config,
        agent,
        git_provider_tokens=git_provider_tokens,
        custom_secrets=custom_secrets,
        selected_repository=selected_repository,
        selected_branch=selected_branch,
    )
    return asyncio.run(coro)


def test_create_runtime_remote_success_round_067(monkeypatch):
    """Remote runtime path: runtime_cls == RemoteRuntime -> ensure override_provider_tokens_with_custom_secret used,
    runtime receives env vars from Secrets, runtime.connect/clone/run_setup/hooks executed and function returns True.
    """
    # Patch module to return FakeRemoteRuntime for get_runtime_cls and RemoteRuntime
    patch_module_for_tests(monkeypatch, remote_runtime_cls=FakeRemoteRuntime)

    dummy = make_dummy_session()

    # Provide a status callback to detect if error path invoked (should not be)
    status_calls = []
    dummy._status_callback = lambda *a: status_calls.append(a)

    # Make agent with sandbox_plugins list which should be forwarded
    agent = SimpleNamespace(sandbox_plugins=[SimpleNamespace(name="p1"), SimpleNamespace(name="p2")])

    # Provide inputs
    git_provider_tokens = {"provider": "orig-token"}
    custom_secrets = {"provider": "secret-token", "EXTRA": "val"}

    # Now run
    result = run_create_runtime(dummy, "remote-runtime", config=object(), agent=agent, git_provider_tokens=git_provider_tokens, custom_secrets=custom_secrets, selected_repository="repo", selected_branch="main")

    # Assertions: success
    assert result is True
    # runtime was created and stored on the dummy self
    assert hasattr(dummy, "runtime") and isinstance(dummy.runtime, FakeRemoteRuntime)
    # override called with the original git_provider_tokens and custom_secrets
    assert dummy._calls.get("override_called_with") == (git_provider_tokens, custom_secrets)
    # runtime should have received the overridden git_provider_tokens (from custom secret)
    assert dummy.runtime._init_kwargs.get("git_provider_tokens") == {"provider": "secret-token"}
    # env_vars comes from Secrets(custom_secrets)
    assert dummy.runtime._init_kwargs.get("env_vars") == {"provider": "secret-token", "EXTRA": "val"}
    # clone args should reflect the passed repository and branch
    assert getattr(dummy.runtime, "clone_args", None) == ({"provider": "secret-token"}, "repo", "main")
    # call_sync_from_async should have invoked the two setup methods (they flip flags)
    assert dummy.runtime.maybe_run_setup_script_called is True
    assert dummy.runtime.maybe_setup_git_hooks_called is True
    # status callback should not have been called in success path
    assert status_calls == []


def test_create_runtime_nonremote_connect_failure_round_067(monkeypatch):
    """Non-Remote runtime path: provider tokens merged via ProviderHandler.get_env_vars, connect raises AgentRuntimeUnavailableError,
    status callback should be invoked with error status and function returns False.
    """
    # For non-remote path, have get_runtime_cls return FakeLocalRuntime but keep RemoteRuntime a different object
    patch_module_for_tests(monkeypatch, remote_runtime_cls=FakeRemoteRuntime)
    # Now override get_runtime_cls specifically to return FakeLocalRuntime (different from RemoteRuntime)
    monkeypatch.setattr(agent_session, "get_runtime_cls", lambda name: FakeLocalRuntime)

    # Patch ProviderHandler to our fake so get_env_vars returns a predictable dict
    monkeypatch.setattr(agent_session, "ProviderHandler", FakeProviderHandler)
    # Use FakeSecrets with no custom secrets
    monkeypatch.setattr(agent_session, "Secrets", FakeSecrets)
    monkeypatch.setattr(agent_session, "call_sync_from_async", lambda f: _call_call_sync_from_async(f))

    dummy = make_dummy_session()

    # capture status callback invocations
    status_calls = []

    def status_cb(*args):
        status_calls.append(args)

    dummy._status_callback = status_cb

    # prepare agent
    agent = SimpleNamespace(sandbox_plugins=[SimpleNamespace(name="p")])

    # Provide tokens; Secrets returns empty env_vars
    git_provider_tokens = {"provider": "tok"}

    # Before running, ensure the FakeLocalRuntime will raise on connect
    # We'll patch the class so instantiation returns an instance configured to raise
    original_local = FakeLocalRuntime

    def local_factory(**kwargs):
        inst = original_local(**kwargs)
        inst._raise_on_connect = True
        return inst

    monkeypatch.setattr(agent_session, "get_runtime_cls", lambda name: local_factory)

    # Call
    result = run_create_runtime(dummy, "some-runtime", config=object(), agent=agent, git_provider_tokens=git_provider_tokens, custom_secrets=None, selected_repository=None, selected_branch=None)

    # Should return False because connect raised
    assert result is False
    # Check that runtime was assigned and is an instance produced by our factory
    assert hasattr(dummy, "runtime") and isinstance(dummy.runtime, FakeLocalRuntime)
    # status callback should have been invoked exactly once with expected error tuple
    assert len(status_calls) == 1
    status_call = status_calls[0]
    # first arg is the level string 'error'
    assert status_call[0] == "error"
    # second arg equals the runtime status enum value for disconnected
    assert status_call[1] == agent_session.RuntimeStatus.ERROR_RUNTIME_DISCONNECTED
    # third arg is the exception message
    assert "simulated-failure" in status_call[2]
