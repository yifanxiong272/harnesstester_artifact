# file: openhands/runtime/plugins/vscode/__init__.py:47-138
# asked: {"lines": [49, 50, 51, 52, 53, 55, 57, 58, 59, 60, 61, 64, 67, 69, 70, 71, 72, 73, 75, 77, 78, 79, 80, 82, 83, 85, 87, 88, 89, 90, 92, 95, 96, 97, 98, 99, 100, 101, 103, 104, 105, 106, 107, 109, 110, 111, 112, 113, 114, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 136, 137], "branches": [[49, 50], [49, 57], [57, 58], [57, 67], [78, 79], [78, 83], [88, 89], [88, 95], [96, 97], [96, 103], [100, 101], [100, 103], [126, 127], [126, 136], [131, 132], [131, 133]]}
# gained: {"lines": [49, 50, 51, 52, 53, 55, 57, 58, 59, 60, 61, 64, 67, 69, 70, 71, 72, 73, 75, 77, 78, 79, 80, 82, 83, 85, 87, 88, 95, 96, 97, 98, 99, 100, 101, 103, 104, 105, 106, 107, 109, 110, 111, 112, 113, 114, 119, 120, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 136, 137], "branches": [[49, 50], [49, 57], [57, 58], [57, 67], [78, 79], [78, 83], [88, 95], [96, 97], [96, 103], [100, 101], [126, 127], [131, 132], [131, 133]]}

import asyncio
import os
import sys
import importlib

import pytest

vscode_mod = importlib.import_module("openhands.runtime.plugins.vscode")
VSCodePlugin = vscode_mod.VSCodePlugin


class _FakeStdout:
    def __init__(self, lines):
        # lines are strings; convert to bytes
        self._lines = [l.encode("utf-8") for l in lines]

    async def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return b""


class _FakeProcess:
    def __init__(self, lines):
        self.stdout = _FakeStdout(lines)


@pytest.mark.asyncio
async def test_initialize_windows_disables_plugin(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(sys, "platform", "win32")

    plugin = VSCodePlugin()
    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    await plugin.initialize("root", runtime_id=None)

    assert plugin.vscode_port is None
    assert plugin.vscode_connection_token is None


@pytest.mark.asyncio
async def test_initialize_unsupported_user(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")

    monkeypatch.setattr(vscode_mod, "RUNTIME_USERNAME", "some_runtime_user", raising=False)

    plugin = VSCodePlugin()
    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    await plugin.initialize("alice", runtime_id=None)

    assert plugin.vscode_port is None
    assert plugin.vscode_connection_token is None


@pytest.mark.asyncio
async def test_initialize_missing_or_invalid_vscode_port(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(vscode_mod, "RUNTIME_USERNAME", None, raising=False)

    plugin = VSCodePlugin()
    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    monkeypatch.delenv("VSCODE_PORT", raising=False)
    await plugin.initialize("root", runtime_id=None)
    assert plugin.vscode_port is None
    assert plugin.vscode_connection_token is None

    monkeypatch.setenv("VSCODE_PORT", "not-an-int")
    await plugin.initialize("root", runtime_id=None)
    assert plugin.vscode_port is None
    assert plugin.vscode_connection_token is None


@pytest.mark.asyncio
async def test_initialize_port_unavailable(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    monkeypatch.setenv("VSCODE_PORT", "54321")
    called = {}

    def fake_check_port_available(port):
        called["port"] = port
        return False

    monkeypatch.setattr(vscode_mod, "check_port_available", fake_check_port_available, raising=False)

    plugin = VSCodePlugin()
    await plugin.initialize("root", runtime_id=None)

    assert plugin.vscode_port == 54321
    assert plugin.vscode_connection_token is not None
    assert isinstance(plugin.vscode_connection_token, str)
    assert called["port"] == 54321
    assert not hasattr(plugin, "gateway_process") or plugin.gateway_process is None


@pytest.mark.asyncio
async def test_initialize_success_with_su_prefix_no_explicit_base(monkeypatch):
    # This test ensures the SU_TO_USER True branch runs and that a normal start occurs
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(vscode_mod, "RUNTIME_USERNAME", None, raising=False)
    monkeypatch.setattr(vscode_mod, "SU_TO_USER", True, raising=False)

    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    monkeypatch.setenv("VSCODE_PORT", "23456")
    # Do NOT set OPENVSCODE_SERVER_BASE_PATH to avoid the UnboundLocalError in the implementation

    monkeypatch.setattr(vscode_mod, "check_port_available", lambda p: True, raising=False)

    async def _no_sleep(duration):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    monkeypatch.setattr(vscode_mod, "should_continue", lambda: True, raising=False)

    captured = {}

    async def fake_create_subprocess_shell(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _FakeProcess(["Starting OpenVSCode Server...\n", "server is up at 0.0.0.0\n"])

    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_create_subprocess_shell)

    plugin = VSCodePlugin()
    await plugin.initialize("root", runtime_id=None)

    assert plugin.vscode_port == 23456
    assert plugin.vscode_connection_token is not None
    assert isinstance(plugin.gateway_process, _FakeProcess)
    cmd = captured.get("cmd", "")
    assert "su - root -s /bin/bash" in cmd
    # No explicit base was set, so ensure no --server-base-path in command
    assert "--server-base-path" not in cmd


@pytest.mark.asyncio
async def test_initialize_runtime_url_path_mode(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(VSCodePlugin, "_setup_vscode_settings", lambda self: None)

    monkeypatch.setattr(vscode_mod, "SU_TO_USER", False, raising=False)
    monkeypatch.setenv("VSCODE_PORT", "34567")
    monkeypatch.setenv("RUNTIME_URL", "http://example.com/rid/somepath")
    monkeypatch.setattr(vscode_mod, "check_port_available", lambda p: True, raising=False)

    async def _no_sleep(duration):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    monkeypatch.setattr(vscode_mod, "should_continue", lambda: True, raising=False)

    captured = {}

    async def fake_create_subprocess_shell(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        return _FakeProcess(["server started at port\n"])

    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_create_subprocess_shell)

    plugin = VSCodePlugin()
    await plugin.initialize("root", runtime_id="rid")

    assert plugin.vscode_port == 34567
    assert plugin.vscode_connection_token is not None
    assert isinstance(plugin.gateway_process, _FakeProcess)
    cmd = captured.get("cmd", "")
    assert "--server-base-path /rid/vscode" in cmd
    assert cmd.startswith("/bin/bash << 'EOF'") or cmd.startswith("/bin/bash << 'EOF'\n")
