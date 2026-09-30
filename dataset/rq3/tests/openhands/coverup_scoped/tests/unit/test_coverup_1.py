# file: openhands/runtime/impl/local/local_runtime.py:227-417
# asked: {"lines": [229, 232, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 248, 249, 251, 253, 254, 255, 261, 262, 263, 265, 266, 267, 269, 270, 273, 274, 275, 276, 280, 281, 284, 285, 287, 288, 290, 292, 293, 297, 298, 299, 301, 302, 305, 306, 307, 308, 309, 310, 313, 314, 318, 319, 321, 322, 324, 325, 328, 331, 332, 333, 334, 335, 336, 337, 338, 339, 342, 343, 345, 346, 347, 349, 350, 353, 355, 356, 357, 358, 362, 363, 364, 365, 366, 367, 371, 372, 374, 376, 379, 380, 381, 382, 383, 384, 385, 386, 387, 390, 391, 393, 395, 396, 398, 399, 400, 402, 403, 404, 408, 409, 411, 412, 413, 414, 416, 417], "branches": [[235, 236], [235, 251], [251, 253], [251, 260], [260, 265], [260, 273], [266, 267], [266, 269], [273, 274], [273, 284], [298, 299], [298, 353], [313, 314], [313, 317], [317, 321], [317, 328], [353, 355], [353, 390], [370, 374], [370, 376], [395, 396], [395, 398], [402, 403], [402, 404], [407, 0], [407, 411], [416, 0], [416, 417]]}
# gained: {"lines": [229, 232, 235, 251, 253, 254, 255, 261, 262, 273, 274, 275, 276, 280, 281, 284, 285, 287, 288, 290, 292, 293, 297, 298, 299, 301, 302, 305, 306, 307, 308, 309, 310, 313, 314, 318, 319, 328, 331, 332, 333, 334, 335, 336, 337, 338, 339, 342, 343, 347, 349, 350, 353, 355, 356, 357, 358, 362, 363, 364, 365, 366, 367, 371, 372, 374, 376, 379, 380, 381, 382, 383, 384, 385, 386, 387, 390, 391, 393, 395, 396, 398, 399, 400, 402, 403, 404, 408, 409, 411, 412, 413, 414, 416, 417], "branches": [[235, 251], [251, 253], [251, 260], [260, 273], [273, 274], [273, 284], [298, 299], [313, 314], [317, 328], [353, 355], [353, 390], [370, 374], [395, 396], [402, 403], [407, 0], [407, 411], [416, 0], [416, 417]]}

import os
import shutil
import tempfile
import types
import threading
import pytest

import openhands.runtime.impl.local.local_runtime as lr
from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.runtime.runtime_status import RuntimeStatus


@pytest.mark.asyncio
async def test_connect_attach_to_existing_raises_and_sets_starting(monkeypatch):
    # Ensure globals are clean
    original_running = lr._RUNNING_SERVERS.copy()
    original_warm = list(lr._WARM_SERVERS)
    lr._RUNNING_SERVERS.clear()
    lr._WARM_SERVERS.clear()
    monkeypatch.delenv('DESIRED_NUM_WARM_SERVERS', raising=False)
    try:
        # Create a LocalRuntime instance without calling its __init__
        inst = object.__new__(lr.LocalRuntime)
        inst.sid = "test-sid-attach"
        inst.attach_to_existing = True
        inst.plugins = []
        # Minimal config object with needed attributes
        inst.config = types.SimpleNamespace()
        inst.config.workspace_base = None
        inst.config.runtime = None
        inst.config.sandbox = types.SimpleNamespace(local_runtime_url="http://localhost")
        inst.config.workspace_mount_path_in_sandbox = None

        logs = []
        def log(level, msg):
            logs.append((level, msg))
        inst.log = log

        status_history = []
        def set_runtime_status(status):
            status_history.append(status)
        inst.set_runtime_status = set_runtime_status

        # Needed callables used later
        inst._wait_until_alive = lambda: None
        inst.setup_initial_env = lambda: None

        # Attempting to connect with attach_to_existing True and no running servers should raise
        with pytest.raises(AgentRuntimeDisconnectedError):
            await inst.connect()

        # Check that we set starting status at the beginning
        assert status_history, "Runtime status was not set at start"
        assert status_history[0] == RuntimeStatus.STARTING_RUNTIME

        # Check that an error log was produced about no existing server
        assert any("No existing server found" in m for (_, m) in logs)
    finally:
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(original_running)
        lr._WARM_SERVERS.clear()
        lr._WARM_SERVERS.extend(original_warm)


@pytest.mark.asyncio
async def test_connect_uses_warm_server_and_creates_additional(monkeypatch, tmp_path):
    # Save and clear globals
    original_running = lr._RUNNING_SERVERS.copy()
    original_warm = list(lr._WARM_SERVERS)
    lr._RUNNING_SERVERS.clear()
    lr._WARM_SERVERS.clear()

    # Prepare a fake warm server whose temp_workspace will be removed
    warm_temp = tempfile.mkdtemp(prefix="warm_temp_")
    server_info = lr.ActionExecutionServerInfo(
        process="proc-warm",
        execution_server_port=9101,
        vscode_port=9102,
        app_ports=[9200],
        log_thread=threading.Thread(target=lambda: None),
        log_thread_exit_event=threading.Event(),
        temp_workspace=warm_temp,
        workspace_mount_path="/warm_mount",
    )
    lr._WARM_SERVERS.append(server_info)

    # Monkeypatch the background warm-server creation to record calls
    created_warm_calls = []
    def fake_create_warm_in_background(config, plugins):
        created_warm_calls.append((config, plugins))
    monkeypatch.setattr(lr, "_create_warm_server_in_background", fake_create_warm_in_background)

    # Set desired number of warm servers to 2 so it creates additional ones
    monkeypatch.setenv('DESIRED_NUM_WARM_SERVERS', '2')

    try:
        # Create a LocalRuntime instance
        inst = object.__new__(lr.LocalRuntime)
        inst.sid = "test-sid-warm"
        inst.attach_to_existing = False
        # Provide workspace_base so that inst._temp_workspace remains None and branch in warm server is tested
        ws_base = tmp_path / "workspace_base"
        inst.config = types.SimpleNamespace()
        inst.config.workspace_base = str(ws_base)
        inst.config.runtime = "not_local"
        inst.config.sandbox = types.SimpleNamespace(local_runtime_url="http://localhost")
        inst.config.workspace_mount_path_in_sandbox = None

        inst.plugins = [types.SimpleNamespace(name="p1")]
        logs = []
        inst.log = lambda level, msg: logs.append((level, msg))

        status_history = []
        inst.set_runtime_status = lambda status: status_history.append(status)

        # These will be called via call_sync_from_async
        inst._wait_until_alive = lambda: None
        inst.setup_initial_env = lambda: None

        # Run connect; it should pop the warm server, remove its temp workspace, and create additional warm servers
        await inst.connect()

        # After connect, the running server should be registered under the sid
        assert inst.sid in lr._RUNNING_SERVERS
        info = lr._RUNNING_SERVERS[inst.sid]
        assert info.execution_server_port == 9101
        # The warm server's temp workspace should have been removed
        assert not os.path.exists(warm_temp)

        # _runtime_initialized should be True
        assert getattr(inst, "_runtime_initialized", False) is True

        # Ensure READY status was set (since attach_to_existing is False)
        assert any(s == RuntimeStatus.READY for s in status_history)

        # Check that additional warm servers were requested to be created (desired=2, after pop there are 0, so create 2)
        assert len(created_warm_calls) == 2
    finally:
        # Cleanup created workspace_base directory
        try:
            shutil.rmtree(str(ws_base))
        except Exception:
            pass
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(original_running)
        lr._WARM_SERVERS.clear()
        lr._WARM_SERVERS.extend(original_warm)
        monkeypatch.delenv('DESIRED_NUM_WARM_SERVERS', raising=False)


@pytest.mark.asyncio
async def test_connect_handles_warm_server_exception_and_uses_create_server(monkeypatch, tmp_path):
    # Save and clear globals
    original_running = lr._RUNNING_SERVERS.copy()
    original_warm = list(lr._WARM_SERVERS)
    lr._RUNNING_SERVERS.clear()
    lr._WARM_SERVERS.clear()

    # Create a dummy _WARM_SERVERS-like object that will raise on pop to hit the exception branch
    class DummyWarm:
        def __bool__(self):
            return True
        def pop(self, idx):
            raise RuntimeError("dummy failure")
    dummy = DummyWarm()
    monkeypatch.setattr(lr, "_WARM_SERVERS", dummy)

    # Prepare server_info to be returned by _create_server
    server_temp = tempfile.mkdtemp(prefix="created_server_temp_")
    server_info = lr.ActionExecutionServerInfo(
        process="proc-created",
        execution_server_port=10101,
        vscode_port=10102,
        app_ports=[10200],
        log_thread=threading.Thread(target=lambda: None),
        log_thread_exit_event=threading.Event(),
        temp_workspace=server_temp,
        workspace_mount_path="/created_mount",
    )
    api_url = "http://localhost:10101"

    def fake_create_server(config, plugins, workspace_prefix):
        return server_info, api_url
    monkeypatch.setattr(lr, "_create_server", fake_create_server)

    try:
        # Create instance
        inst = object.__new__(lr.LocalRuntime)
        inst.sid = "test-sid-create"
        inst.attach_to_existing = False
        inst.plugins = []
        inst.config = types.SimpleNamespace()
        # Set workspace_base None to create a temp dir for this runtime
        inst.config.workspace_base = None
        inst.config.runtime = None
        inst.config.sandbox = types.SimpleNamespace(local_runtime_url="http://localhost")
        inst.config.workspace_mount_path_in_sandbox = None

        logs = []
        inst.log = lambda level, msg: logs.append((level, msg))

        status_history = []
        inst.set_runtime_status = lambda status: status_history.append(status)

        # these are invoked via call_sync_from_async
        inst._wait_until_alive = lambda: None
        inst.setup_initial_env = lambda: None

        # Run connect; it should handle the exception from warm server handling and then call _create_server
        await inst.connect()

        # Ensure that the created server's temp workspace got removed because server_info.temp_workspace != inst._temp_workspace
        assert not os.path.exists(server_temp)

        # Ensure running server is stored
        assert inst.sid in lr._RUNNING_SERVERS
        stored = lr._RUNNING_SERVERS[inst.sid]
        assert stored.execution_server_port == 10101
        assert inst.api_url == api_url

        # runtime initialized
        assert getattr(inst, "_runtime_initialized", False) is True

        # Check that an error log about warm server usage was recorded
        assert any("Error using warm server" in m or "No warm servers available" in m for (_, m) in logs)
    finally:
        # Restore _WARM_SERVERS to original list object
        monkeypatch.setattr(lr, "_WARM_SERVERS", original_warm)
        lr._RUNNING_SERVERS.clear()
        lr._RUNNING_SERVERS.update(original_running)
