# file: openhands/server/session/agent_session.py:304-392
# asked: {"lines": [324, 325, 327, 328, 330, 331, 332, 335, 336, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354, 355, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 373, 374, 375, 376, 377, 378, 379, 381, 383, 384, 386, 387, 389, 390, 392], "branches": [[324, 325], [324, 327], [332, 335], [332, 353], [377, 378], [377, 381]]}
# gained: {"lines": [324, 325, 327, 328, 330, 331, 332, 335, 336, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 353, 354, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 373, 374, 375, 376, 377, 378, 379, 381, 383, 384, 386, 387, 389, 390, 392], "branches": [[324, 325], [324, 327], [332, 335], [332, 353], [377, 378]]}

import asyncio
import pytest

from types import SimpleNamespace

import openhands.server.session.agent_session as agent_session_mod
from openhands.core.exceptions import AgentRuntimeUnavailableError


# Helper fakes
class FakeEventStream:
    def __init__(self, sid, file_store, user_id):
        self.sid = sid
        self.file_store = file_store
        self.user_id = user_id


class FakeLogger:
    def __init__(self, *args, **kwargs):
        self.logs = []

    def debug(self, *args, **kwargs):
        self.logs.append(("debug", args))

    def error(self, *args, **kwargs):
        self.logs.append(("error", args))


class FakeSecrets:
    def __init__(self, custom_secrets=None):
        self._custom = dict(custom_secrets or {})

    def get_env_vars(self):
        # Return a shallow copy to simulate real behaviour
        return dict(self._custom)


class FakeProviderHandler:
    def __init__(self, provider_tokens=None):
        self.provider_tokens = dict(provider_tokens or {})
        self.get_env_vars_called = False

    async def get_env_vars(self, expose_secrets=True):
        self.get_env_vars_called = True
        return {"PROVIDER_KEY": "PROVIDER_VAL"}


class FakePlugin:
    def __init__(self, name):
        self.name = name


class FakeRemoteRuntime:
    def __init__(self, **kwargs):
        # store what was passed for assertions
        self._init_kwargs = kwargs
        # default plugin list, but if plugins passed, use it
        self.plugins = kwargs.get("plugins", [FakePlugin(name="p1")])
        # flags for call_sync_from_async side effects
        self.setup_run = False
        self.hooks_setup = False

    async def connect(self):
        # successful connect
        self.connected = True

    async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
        self.clone_called = (git_provider_tokens, selected_repository, selected_branch)

    def maybe_run_setup_script(self):
        self.setup_run = True

    def maybe_setup_git_hooks(self):
        self.hooks_setup = True


class FakeOtherRuntime:
    def __init__(self, **kwargs):
        self._init_kwargs = kwargs
        self.plugins = kwargs.get("plugins", [FakePlugin(name="p2")])

    async def connect(self):
        self.connected = True

    async def clone_or_init_repo(self, git_provider_tokens, selected_repository, selected_branch):
        self.clone_called = (git_provider_tokens, selected_repository, selected_branch)

    def maybe_run_setup_script(self):
        self.setup_run = True

    def maybe_setup_git_hooks(self):
        self.hooks_setup = True


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    """
    Patch out environment pieces used in AgentSession so tests are isolated and
    don't depend on large parts of the real system.
    """
    # Replace EventStream and the logger adapter with fakes
    monkeypatch.setattr(agent_session_mod, "EventStream", FakeEventStream)
    monkeypatch.setattr(agent_session_mod, "OpenHandsLoggerAdapter", lambda *args, **kwargs: FakeLogger())

    # Replace Secrets and ProviderHandler
    monkeypatch.setattr(agent_session_mod, "Secrets", FakeSecrets)
    monkeypatch.setattr(agent_session_mod, "ProviderHandler", FakeProviderHandler)

    # Replace call_sync_from_async to synchronously call the function inside an awaitable
    async def fake_call_sync_from_async(func, *args, **kwargs):
        if callable(func):
            func()
        return None

    monkeypatch.setattr(agent_session_mod, "call_sync_from_async", fake_call_sync_from_async)

    yield
    # monkeypatch fixture auto-cleans


@pytest.mark.asyncio
async def test_create_runtime_raises_if_already_created():
    # Prepare minimal dependencies
    sid = "session-1"
    file_store = object()
    llm_registry = object()
    conversation_stats = object()

    session = agent_session_mod.AgentSession(sid, file_store, llm_registry, conversation_stats)

    # Simulate runtime already present
    session.runtime = object()

    with pytest.raises(RuntimeError) as exc:
        await session._create_runtime(
            runtime_name="irrelevant",
            config=object(),
            agent=SimpleNamespace(sandbox_plugins=[]),
        )
    assert "Runtime already created" in str(exc.value)


@pytest.mark.asyncio
async def test_create_runtime_remote_runtime_success(monkeypatch):
    sid = "session-remote"
    file_store = object()
    llm_registry = object()
    conversation_stats = object()

    session = agent_session_mod.AgentSession(sid, file_store, llm_registry, conversation_stats)

    # Ensure module's RemoteRuntime is our FakeRemoteRuntime, so comparison in code succeeds
    monkeypatch.setattr(agent_session_mod, "RemoteRuntime", FakeRemoteRuntime)
    # get_runtime_cls should return the module RemoteRuntime (now FakeRemoteRuntime)
    monkeypatch.setattr(agent_session_mod, "get_runtime_cls", lambda name: agent_session_mod.RemoteRuntime)

    # Ensure override_provider_tokens_with_custom_secret is called and returns expected tokens
    def fake_override(tokens, custom):
        return {"OVERRIDDEN": "YES"}

    session.override_provider_tokens_with_custom_secret = fake_override

    # Prepare an agent with sandbox_plugins attribute
    agent = SimpleNamespace(sandbox_plugins=[FakePlugin("pA"), FakePlugin("pB")])

    # Call with custom secrets to test Secrets pipeline
    custom_secrets = {"CUSTOM_KEY": "CUSTOM_VAL"}

    result = await session._create_runtime(
        runtime_name="remote",
        config=object(),
        agent=agent,
        git_provider_tokens={"GH": "token"},
        custom_secrets=custom_secrets,
        selected_repository="repo",
        selected_branch="main",
    )

    # Should have initialized and returned True
    assert result is True
    assert isinstance(session.runtime, FakeRemoteRuntime)

    # The FakeRemoteRuntime should have received overrided tokens via the kw args
    assert session.runtime._init_kwargs.get("git_provider_tokens") == {"OVERRIDDEN": "YES"}

    # Ensure that the env_vars from Secrets made it through to runtime init kwargs
    assert "env_vars" in session.runtime._init_kwargs
    assert session.runtime._init_kwargs["env_vars"].get("CUSTOM_KEY") == "CUSTOM_VAL"

    # Confirm that the sync setup functions were executed via fake call_sync_from_async
    assert getattr(session.runtime, "setup_run", False) is True
    assert getattr(session.runtime, "hooks_setup", False) is True

    # Plugins list used in logging should reflect our plugin names
    plugin_names = [p.name for p in session.runtime.plugins]
    assert plugin_names == ["pA", "pB"]


@pytest.mark.asyncio
async def test_create_runtime_non_remote_and_connect_failure_reports_status(monkeypatch):
    sid = "session-nonremote"
    file_store = object()
    llm_registry = object()
    conversation_stats = object()

    status_calls = []

    def status_callback(kind, code, message):
        status_calls.append((kind, code, message))

    session = agent_session_mod.AgentSession(sid, file_store, llm_registry, conversation_stats, status_callback=status_callback)

    # Make get_runtime_cls return a non-Remote runtime class
    monkeypatch.setattr(agent_session_mod, "get_runtime_cls", lambda name: FakeOtherRuntime)

    # Replace ProviderHandler with our FakeProviderHandler to test get_env_vars merge
    monkeypatch.setattr(agent_session_mod, "ProviderHandler", FakeProviderHandler)

    agent = SimpleNamespace(sandbox_plugins=[FakePlugin("pX")])

    # Now monkeypatch the FakeOtherRuntime.connect to raise AgentRuntimeUnavailableError
    async def failing_connect(self):
        raise AgentRuntimeUnavailableError("cannot connect right now")

    monkeypatch.setattr(FakeOtherRuntime, "connect", failing_connect, raising=False)

    result = await session._create_runtime(
        runtime_name="other",
        config=object(),
        agent=agent,
        git_provider_tokens={"PROV": "T"},
        custom_secrets=None,
        selected_repository=None,
        selected_branch=None,
    )

    assert result is False

    assert len(status_calls) == 1
    kind, code, message = status_calls[0]
    assert kind == "error"
    assert code == agent_session_mod.RuntimeStatus.ERROR_RUNTIME_DISCONNECTED
    assert "cannot connect right now" in message

    # Ensure that runtime attribute exists (construction happened before connect)
    assert isinstance(session.runtime, FakeOtherRuntime)
    # Ensure that env_vars passed to the runtime included provider handler env entries
    assert "env_vars" in session.runtime._init_kwargs
    assert session.runtime._init_kwargs["env_vars"].get("PROVIDER_KEY") == "PROVIDER_VAL"
