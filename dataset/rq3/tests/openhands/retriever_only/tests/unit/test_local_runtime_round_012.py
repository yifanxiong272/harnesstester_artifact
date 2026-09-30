import os
import tempfile
import types
import importlib
import pytest

module_path = "openhands.runtime.impl.local.local_runtime"
mod = importlib.import_module(module_path)

ActionExecutionServerInfo = mod.ActionExecutionServerInfo
AgentRuntimeDisconnectedError = mod.AgentRuntimeDisconnectedError

async def _noop():
    return None

def make_runtime_obj(sid="sid1", attach_to_existing=False):
    # Create an instance without running __init__ to avoid heavy dependencies
    runtime = mod.LocalRuntime.__new__(mod.LocalRuntime)

    # Minimal config object expected by connect
    sandbox = types.SimpleNamespace(local_runtime_url="http://localhost")
    config = types.SimpleNamespace(
        workspace_base=None,
        runtime="local",
        sandbox=sandbox,
        workspace_mount_path_in_sandbox=None,
    )

    runtime.sid = sid
    runtime.attach_to_existing = attach_to_existing
    runtime.config = config
    runtime.plugins = []

    # recorders
    runtime._logs = []
    runtime._statuses = []

    def log(level, msg):
        runtime._logs.append((level, msg))

    def set_runtime_status(s):
        runtime._statuses.append(s)

    # Provide trivial sync functions that will be wrapped by call_sync_from_async
    runtime._wait_until_alive = lambda: None
    runtime.setup_initial_env = lambda: None

    runtime.log = log
    runtime.set_runtime_status = set_runtime_status

    # ensure attributes that connect will set exist
    runtime.server_process = None
    runtime._execution_server_port = None
    runtime._log_thread = None
    runtime._log_thread_exit_event = None
    runtime._vscode_port = None
    runtime._app_ports = None
    runtime._temp_workspace = None
    runtime.api_url = None
    runtime._runtime_initialized = False

    return runtime

@pytest.mark.asyncio
async def test_connect_existing_server_round_012(tmp_path, monkeypatch):
    # Arrange: Put a running server for this sid
    sid = "session-existing"
    runtime = make_runtime_obj(sid=sid, attach_to_existing=False)

    # Make a server_info that the runtime will pick up
    server_info = ActionExecutionServerInfo(
        process="proc",
        execution_server_port=9999,
        vscode_port=8888,
        app_ports=[3000],
        log_thread="lt",
        log_thread_exit_event="lte",
        temp_workspace="/tmp/some_temp",
        workspace_mount_path="/the/mount",
    )

    # Ensure module-level globals are in known state
    monkeypatch.setattr(mod, "_RUNNING_SERVERS", {sid: server_info})
    monkeypatch.setattr(mod, "_WARM_SERVERS", [])

    # Act
    await mod.LocalRuntime.connect(runtime)

    # Assert: the runtime should have adopted the server info values
    assert runtime.server_process == "proc"
    assert runtime._execution_server_port == 9999
    assert runtime.api_url == f"{runtime.config.sandbox.local_runtime_url}:9999"
    assert runtime.config.workspace_mount_path_in_sandbox == "/the/mount"
    # runtime should be marked initialized
    assert runtime._runtime_initialized is True
    # log must have at least one info message about waiting for server
    assert any("Waiting for server to become ready" in msg for _, msg in runtime._logs)


@pytest.mark.asyncio
async def test_connect_attach_to_existing_no_server_raises_round_012(monkeypatch):
    # Arrange: no running server and attach_to_existing = True
    sid = "session-missing"
    runtime = make_runtime_obj(sid=sid, attach_to_existing=True)

    monkeypatch.setattr(mod, "_RUNNING_SERVERS", {})
    monkeypatch.setattr(mod, "_WARM_SERVERS", [])

    # Act & Assert
    with pytest.raises(AgentRuntimeDisconnectedError) as exc:
        await mod.LocalRuntime.connect(runtime)

    assert f"No existing server found for session {sid}" in str(exc.value)
    # ensure an error log entry was made
    assert any(level == 'error' and 'No existing server found' in msg for level, msg in runtime._logs)


@pytest.mark.asyncio
async def test_connect_workspace_and_create_server_round_012(tmp_path, monkeypatch):
    # Arrange: simulate LOCAL_WORKSPACE_BASE env set and no warm servers, and _create_server returns a server
    sid = "session-new"
    runtime = make_runtime_obj(sid=sid, attach_to_existing=False)

    # point LOCAL_WORKSPACE_BASE to a temp dir (will exist)
    env_base = str(tmp_path / "local_base")
    os.makedirs(env_base, exist_ok=True)
    monkeypatch.setenv('LOCAL_WORKSPACE_BASE', env_base)

    # ensure DESIRED_NUM_WARM_SERVERS triggers creation of additional warm servers
    monkeypatch.setenv('DESIRED_NUM_WARM_SERVERS', '2')

    # Reset module globals
    monkeypatch.setattr(mod, "_RUNNING_SERVERS", {})
    monkeypatch.setattr(mod, "_WARM_SERVERS", [])

    # Track calls to create_warm_server_in_background
    created_background = []

    def fake_create_warm_server_in_background(cfg, plugins):
        created_background.append((cfg, tuple(plugins)))

    monkeypatch.setattr(mod, "_create_warm_server_in_background", fake_create_warm_server_in_background)

    # Track calls to shutil.rmtree to avoid deleting anything
    monkeypatch.setattr(mod, "shutil", mod.shutil)
    # monkeypatch the specific rmtree used in module
    called_rmtree = []

    def fake_rmtree(path):
        called_rmtree.append(path)

    monkeypatch.setattr(mod, "shutil", types.SimpleNamespace(rmtree=fake_rmtree))

    # Fake server_info returned by _create_server: has a temp_workspace that differs from runtime._temp_workspace
    fake_server_info = ActionExecutionServerInfo(
        process="newproc",
        execution_server_port=4242,
        vscode_port=1111,
        app_ports=[4000],
        log_thread="lt2",
        log_thread_exit_event="lte2",
        temp_workspace="/tmp/other_temp_created",
        workspace_mount_path="/mount/from/create",
    )

    def fake_create_server(config, plugins, workspace_prefix):
        return fake_server_info, f"{config.sandbox.local_runtime_url}:4242"

    monkeypatch.setattr(mod, "_create_server", fake_create_server)

    # Act
    await mod.LocalRuntime.connect(runtime)

    # Assert: _create_server used -> runtime fields set accordingly
    assert runtime.server_process == "newproc"
    assert runtime._execution_server_port == 4242
    assert runtime.api_url == f"{runtime.config.sandbox.local_runtime_url}:4242"

    # The temp workspace returned by fake_create_server should have been rmtree'd because it's different
    assert "/tmp/other_temp_created" in called_rmtree

    # _RUNNING_SERVERS should now contain the sid
    assert sid in mod._RUNNING_SERVERS
    # Because DESIRED_NUM_WARM_SERVERS was 2 and _WARM_SERVERS was empty, two additional background warm servers should be requested
    assert len(created_background) == 2

    # cleanup environment variables we set
    monkeypatch.delenv('LOCAL_WORKSPACE_BASE', raising=False)
    monkeypatch.delenv('DESIRED_NUM_WARM_SERVERS', raising=False)
