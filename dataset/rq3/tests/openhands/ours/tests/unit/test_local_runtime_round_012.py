import asyncio
import os
from types import SimpleNamespace
import pytest

from openhands.runtime.impl.local import local_runtime as lr


def make_stub_runtime(sid="sid", attach_to_existing=False):
    # Create an uninitialized LocalRuntime instance and set only the attributes
    inst = lr.LocalRuntime.__new__(lr.LocalRuntime)
    inst.sid = sid
    inst.attach_to_existing = attach_to_existing
    inst.plugins = []
    # Minimal config object shape used by connect
    inst.config = SimpleNamespace()
    inst.config.sandbox = SimpleNamespace(local_runtime_url="http://localhost")
    inst.config.workspace_base = None
    inst.config.runtime = "local"
    inst.config.workspace_mount_path_in_sandbox = None

    # Tracking state
    inst.server_process = None
    inst._execution_server_port = None
    inst._log_thread = None
    inst._log_thread_exit_event = None
    inst._vscode_port = None
    inst._app_ports = None
    inst._temp_workspace = None
    inst._runtime_initialized = False

    # Provide methods expected by connect
    def set_runtime_status(status):
        inst._last_status = status

    def log(level, msg):
        # record last log for assertions if needed
        inst._last_log = (level, msg)

    # Provide simple sync functions to be called inside call_sync_from_async
    def _wait_until_alive():
        return None

    def setup_initial_env():
        inst._setup_initial_env_called = True

    inst.set_runtime_status = set_runtime_status
    inst.log = log
    inst._wait_until_alive = _wait_until_alive
    inst.setup_initial_env = setup_initial_env

    return inst


@pytest.mark.asyncio
async def test_connect_existing_server_and_warm_creation_round_012():
    # Prepare module-level globals and patches
    prev_running = dict(lr._RUNNING_SERVERS)
    prev_warm = list(getattr(lr, "_WARM_SERVERS", []))
    prev_desired = os.environ.get("DESIRED_NUM_WARM_SERVERS")
    created_background = []

    # Fake call_sync_from_async to be awaitable and run the passed callable immediately
    async def fake_call_sync_from_async(func):
        # if func is callable, call it synchronously
        if callable(func):
            func()
        return None

    prev_call_sync = lr.call_sync_from_async
    lr.call_sync_from_async = fake_call_sync_from_async

    # patch background warm-creation collector
    prev_create_bg = lr._create_warm_server_in_background

    def fake_create_warm_server_in_background(config, plugins):
        created_background.append((config, plugins))

    lr._create_warm_server_in_background = fake_create_warm_server_in_background

    try:
        # Put an existing server entry for this session id
        sid = "existing_sid"
        server_info = lr.ActionExecutionServerInfo(
            process="proc",
            execution_server_port=12345,
            vscode_port=2222,
            app_ports={},
            log_thread=None,
            log_thread_exit_event=None,
            temp_workspace=None,
            workspace_mount_path="/host/mount",
        )
        lr._RUNNING_SERVERS[sid] = server_info

        # Desired warm servers set higher than current (0)
        os.environ["DESIRED_NUM_WARM_SERVERS"] = "1"

        rt = make_stub_runtime(sid=sid, attach_to_existing=False)

        # Run connect
        await rt.connect()

        # Assertions: existing server path used, api_url set from server_info port
        assert rt.api_url == f"{rt.config.sandbox.local_runtime_url}:{server_info.execution_server_port}"
        assert rt._runtime_initialized is True

        # Because desired warm servers > len(_WARM_SERVERS)=0, background creator should be called
        assert len(created_background) == 1
        # The global running servers should still contain our sid entry after connect
        assert sid in lr._RUNNING_SERVERS
    finally:
        # restore
        lr.call_sync_from_async = prev_call_sync
        lr._create_warm_server_in_background = prev_create_bg
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(prev_running)
        lr._WARM_SERVERS = list(prev_warm)
        if prev_desired is None:
            os.environ.pop("DESIRED_NUM_WARM_SERVERS", None)
        else:
            os.environ["DESIRED_NUM_WARM_SERVERS"] = prev_desired


def test_connect_attach_to_existing_no_server_raises_round_012():
    # No server present and attach_to_existing True should raise AgentRuntimeDisconnectedError
    prev_running = dict(lr._RUNNING_SERVERS)
    try:
        sid = "missing"
        if sid in lr._RUNNING_SERVERS:
            del lr._RUNNING_SERVERS[sid]

        rt = make_stub_runtime(sid=sid, attach_to_existing=True)

        # use asyncio.run since this test is synchronous pytest function
        with pytest.raises(lr.AgentRuntimeDisconnectedError):
            asyncio.run(rt.connect())
    finally:
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(prev_running)


@pytest.mark.asyncio
async def test_connect_warm_server_pop_and_temp_workspace_round_012():
    prev_warm = list(getattr(lr, "_WARM_SERVERS", []))
    prev_running = dict(lr._RUNNING_SERVERS)
    prev_mkdtemp = lr.tempfile.mkdtemp
    prev_rmtree = lr.shutil.rmtree
    prev_call_sync = lr.call_sync_from_async

    # Capture rmtree calls
    rmtree_calls = []

    def fake_rmtree(path):
        rmtree_calls.append(path)

    # Make mkdtemp deterministic
    def fake_mkdtemp(prefix=None):
        return "/tmp/new_workspace_for_test"

    async def fake_call_sync_from_async(func):
        if callable(func):
            func()
        return None

    lr.tempfile.mkdtemp = fake_mkdtemp
    lr.shutil.rmtree = fake_rmtree
    lr.call_sync_from_async = fake_call_sync_from_async

    try:
        # Provide one warm server with an existing temp workspace path
        sid = "warm_sid"
        warm_info = lr.ActionExecutionServerInfo(
            process="warm_proc",
            execution_server_port=55555,
            vscode_port=3333,
            app_ports={},
            log_thread=None,
            log_thread_exit_event=None,
            temp_workspace="/tmp/warm_tmp",
            workspace_mount_path="/host/warm",
        )
        lr._WARM_SERVERS = [warm_info]

        rt = make_stub_runtime(sid=sid, attach_to_existing=False)
        # ensure config.workspace_base is None to follow temp workspace creation path
        rt.config.workspace_base = None

        await rt.connect()

        # rmtree should have been called to remove the warm server's temp workspace
        assert "/tmp/warm_tmp" in rmtree_calls

        # The runtime should have created a new temp workspace and used it
        assert rt.config.workspace_mount_path_in_sandbox == "/tmp/new_workspace_for_test"

        # And the running servers dict should have been updated for this sid
        assert sid in lr._RUNNING_SERVERS
    finally:
        lr.tempfile.mkdtemp = prev_mkdtemp
        lr.shutil.rmtree = prev_rmtree
        lr.call_sync_from_async = prev_call_sync
        lr._WARM_SERVERS = list(prev_warm)
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(prev_running)
