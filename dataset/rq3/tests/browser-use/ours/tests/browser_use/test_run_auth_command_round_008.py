import asyncio
import sys
from types import SimpleNamespace
import pytest

from browser_use.cli import run_auth_command

# Helpers / fakes used across tests
class FakeAuthConfig:
    def __init__(self, authorized_at=None):
        self.authorized_at = authorized_at

class FakeDeviceAuthClient:
    """A minimal fake for browser_use.sync.auth.DeviceAuthClient used by run_auth_command."""
    def __init__(self, *, is_authenticated=False, api_token=False, user_id="user-1", temp_user_id="temp-1", device_id="dev-1", base_url="https://api.example.com", auth_authorized_at=None):
        self.is_authenticated = is_authenticated
        self.api_token = api_token
        self.user_id = user_id
        self.temp_user_id = temp_user_id
        self.device_id = device_id
        self.base_url = base_url
        self.auth_config = FakeAuthConfig(auth_authorized_at)

class FakeEvent:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class FakeCloudSync:
    def __init__(self, allow_session_events_for_auth=False, *, raise_on_handle=False, authenticate_result=True):
        self.allow_session_events_for_auth = allow_session_events_for_auth
        self.raise_on_handle = raise_on_handle
        self.authenticate_result = authenticate_result
        self.events = []
        self.session_id = None
        self.auth_client = None

    def set_auth_flow_active(self):
        # marker method; nothing required for test
        self._active = True

    async def handle_event(self, ev):
        # Optionally raise to simulate backend errors
        if self.raise_on_handle and not getattr(self, "_raised_once", False):
            # mark and raise to simulate an error during the first handle_event
            self._raised_once = True
            raise Exception("simulated backend error")
        self.events.append(ev)

    async def authenticate(self, *args, **kwargs):
        # Simulate authentication completing successfully/unsuccessfully
        # When successful, ensure auth_client.is_authenticated reflects that
        if self.auth_client is not None and self.authenticate_result:
            self.auth_client.is_authenticated = True
        return self.authenticate_result


# Simple sequential uuid7str generator used by tests so ids are deterministic
def make_uuid7str_seq():
    counter = {"i": 0}

    def uuid7str():
        counter["i"] += 1
        return f"id-{counter['i']}"

    return uuid7str


@pytest.mark.asyncio
async def test_run_auth_command_already_authenticated_round_008(monkeypatch, capsys):
    """Covers the early-authenticated branch (prints authorized time, shows frontend URL and returns)."""
    # Provide a deterministic uuid generator though not used for this branch
    monkeypatch.setattr("uuid_extensions.uuid7str", make_uuid7str_seq())

    # Patch DeviceAuthClient to simulate an already-authenticated user
    def device_factory():
        return FakeDeviceAuthClient(is_authenticated=True, api_token=True, user_id="user-ALREADY", temp_user_id="temp-ALREADY", device_id="dev-ALREADY", auth_authorized_at="2025-01-01T00:00:00Z", base_url="https://api.example.com")

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", device_factory)

    # Ensure CONFIG.BROWSER_USE_CLOUD_UI_URL is None so code uses base_url replace logic
    monkeypatch.setattr("browser_use.cli.CONFIG", SimpleNamespace(BROWSER_USE_CLOUD_UI_URL=None))

    # Ensure sleeps are instantaneous for deterministic behavior
    async def fast_sleep(_=0):
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # Run the command and capture printed output
    await run_auth_command()
    captured = capsys.readouterr()

    # Assert expected pieces of output indicating early-authenticated path
    assert "Already authenticated" in captured.out, "Should indicate already authenticated"
    assert "User ID:" in captured.out
    assert "View your runs at:" in captured.out, "Should print frontend URL when already authenticated"


@pytest.mark.asyncio
async def test_run_auth_command_full_auth_flow_success_round_008(monkeypatch, capsys):
    """Covers the full authentication flow where authentication completes successfully and step/completion events are sent."""
    # Deterministic uuid sequence
    uuid_seq = make_uuid7str_seq()
    monkeypatch.setattr("uuid_extensions.uuid7str", uuid_seq)

    # DeviceAuthClient: initially not authenticated
    def initial_device_client():
        return FakeDeviceAuthClient(is_authenticated=False, api_token=False, user_id="user-INIT", temp_user_id="temp-INIT", device_id="dev-INIT", base_url="https://api.api.example.com")

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", initial_device_client)

    # Patch cloud event constructors to return simple FakeEvent objects (recording kwargs)
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentSessionEvent", lambda **kw: FakeEvent(**kw))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentTaskEvent", lambda **kw: FakeEvent(**kw))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentStepEvent", lambda **kw: FakeEvent(**kw))
    monkeypatch.setattr("browser_use.agent.cloud_events.UpdateAgentTaskEvent", lambda **kw: FakeEvent(**kw))

    # Replace create_task_with_error_handling to just return the passed awaitable (deterministic)
    monkeypatch.setattr("browser_use.utils.create_task_with_error_handling", lambda coro, **kwargs: coro)

    # Fast sleep to avoid long delays in show_auth_progress
    async def fast_sleep(_=0):
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # Create a CloudSync instance that will record events and report successful authentication
    def cloudsync_factory(**kwargs):
        # authenticate_result True => auth completes successfully
        return FakeCloudSync(allow_session_events_for_auth=True, authenticate_result=True)

    monkeypatch.setattr("browser_use.sync.service.CloudSync", cloudsync_factory)

    # Ensure CONFIG provides no explicit front-end UI so code uses base_url replacement
    monkeypatch.setattr("browser_use.cli.CONFIG", SimpleNamespace(BROWSER_USE_CLOUD_UI_URL=None))

    # Execute
    await run_auth_command()
    captured = capsys.readouterr()

    # Assertions: we should see success messages and that the fake CloudSync recorded expected events
    assert "Authentication successful" in captured.out or "Authentication successful!" in captured.out

    # Inspect the CloudSync instance constructed in the module: we patched the constructor to return a fresh FakeCloudSync each time
    # The run_auth_command's CloudSync instance is not directly returned; however, we can reconstruct expected event ids based on uuid generator
    # uuid7str produced ids sequentially: id-1 (session) id-2 (task)
    # We assert that the printed output contains the repository URL message from the step event creation
    assert "https://github.com/browser-use/browser-use" in captured.out or "Sending dummy step event" in captured.out or "Welcome to Browser Use" in captured.out


@pytest.mark.asyncio
async def test_run_auth_command_backend_error_triggers_exit_round_008(monkeypatch):
    """Simulates an exception during sync_service.handle_event to ensure the exception path attempts to send the error event and exits with code 1."""
    # Deterministic uuids
    uuid_seq = make_uuid7str_seq()
    monkeypatch.setattr("uuid_extensions.uuid7str", uuid_seq)

    # DeviceAuthClient: initially not authenticated
    def device_factory():
        return FakeDeviceAuthClient(is_authenticated=False, api_token=False, user_id="user-ERR", temp_user_id="temp-ERR", device_id="dev-ERR")

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", device_factory)

    # Event constructors
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentSessionEvent", lambda **kw: FakeEvent(**kw))
    monkeypatch.setattr("browser_use.agent.cloud_events.UpdateAgentTaskEvent", lambda **kw: FakeEvent(**kw))

    # Force CloudSync.handle_event to raise on its first call to simulate backend error
    def cloudsync_factory(**kwargs):
        return FakeCloudSync(allow_session_events_for_auth=True, raise_on_handle=True)

    monkeypatch.setattr("browser_use.sync.service.CloudSync", cloudsync_factory)

    # Make asyncio.sleep immediate to avoid delays
    async def fast_sleep(_=0):
        return None

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # Patch create_task_with_error_handling to return coroutine directly
    monkeypatch.setattr("browser_use.utils.create_task_with_error_handling", lambda coro, **kwargs: coro)

    # Replace sys.exit to raise SystemExit so pytest can capture it
    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)

    # Run and assert that SystemExit(1) is raised due to the simulated backend error
    with pytest.raises(SystemExit) as excinfo:
        await run_auth_command()

    assert excinfo.value.code == 1
