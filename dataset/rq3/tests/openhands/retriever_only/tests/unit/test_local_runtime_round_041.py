import sys
import types
import os
import subprocess
import pytest

from openhands.runtime.impl.local.local_runtime import check_dependencies


def _make_libtmux_module(server_obj):
    m = types.ModuleType("libtmux")
    class Server:
        def __init__(self):
            self._server = server_obj
        def new_session(self, session_name=None):
            return self._server.new_session(session_name=session_name)
    m.Server = Server
    return m


def _make_browser_env_module(close_called_container):
    # create nested modules so the import path works
    pkg = types.ModuleType("openhands")
    runtime_pkg = types.ModuleType("openhands.runtime")
    browser_pkg = types.ModuleType("openhands.runtime.browser")
    env_mod = types.ModuleType("openhands.runtime.browser.browser_env")

    class BrowserEnv:
        def __init__(self):
            self._closed = False
        def close(self):
            self._closed = True
            close_called_container.append(True)

    env_mod.BrowserEnv = BrowserEnv
    return {"openhands": pkg, "openhands.runtime": runtime_pkg, "openhands.runtime.browser": browser_pkg, "openhands.runtime.browser.browser_env": env_mod}


def test_path_not_exists_round_041(monkeypatch):
    # os.path.exists -> False should raise with a helpful message
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    with pytest.raises(ValueError) as exc:
        check_dependencies("/not/a/path", check_browser=False)
    msg = str(exc.value)
    assert "does not exist" in msg
    assert "Please follow the instructions" in msg


def test_jupyter_missing_round_041(monkeypatch):
    # Path exists but jupyter not found in check_output output -> raises
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "version 1.2.3")
    monkeypatch.setattr(sys, "platform", sys.platform, raising=False)  # ensure modifiable but leave platform
    with pytest.raises(ValueError) as exc:
        check_dependencies("/some/path", check_browser=False)
    assert "Jupyter is not properly installed" in str(exc.value)


def test_skip_libtmux_on_windows_round_041(monkeypatch):
    # On Windows, libtmux checks are skipped; function should complete when jupyter is OK
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "jupyter 1.0")
    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    # No libtmux import should happen. Should not raise.
    check_dependencies("/some/path", check_browser=False)


def test_libtmux_new_session_failure_round_041(monkeypatch):
    # libtmux.Server().new_session raises -> should raise a ValueError about tmux availability
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "jupyter 1.0")
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    class FakeServerObj:
        def new_session(self, session_name=None):
            raise Exception("no tmux available")

    libtmux_mod = _make_libtmux_module(FakeServerObj())
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    with pytest.raises(ValueError) as exc:
        check_dependencies("/some/path", check_browser=False)
    assert "tmux is not properly installed" in str(exc.value) or "tmux is not properly installed or available on the path" in str(exc.value)


def test_libtmux_pane_output_missing_round_041(monkeypatch):
    # libtmux present but pane output does not contain the expected 'test' -> error
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "jupyter 2.0")
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    class FakePane:
        def send_keys(self, *a, **k):
            pass
        def cmd(self, *a, **k):
            # emulate capture-pane returning stdout without the word 'test'
            return types.SimpleNamespace(stdout=["no matching output"])

    class FakeSession:
        def __init__(self):
            self.active_pane = FakePane()
            self.killed = False
        def kill(self):
            self.killed = True

    class FakeServerObj:
        def new_session(self, session_name=None):
            return FakeSession()

    libtmux_mod = _make_libtmux_module(FakeServerObj())
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    with pytest.raises(ValueError) as exc:
        check_dependencies("/some/path", check_browser=False)
    assert "libtmux is not properly installed" in str(exc.value)


def test_full_success_with_browser_round_041(monkeypatch):
    # Successful path: jupyter ok, libtmux works and pane contains 'test', and BrowserEnv.close is called
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "jupyter 3.0")
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    class FakePane:
        def __init__(self):
            self.sent = []
        def send_keys(self, value):
            self.sent.append(value)
        def cmd(self, *a, **k):
            return types.SimpleNamespace(stdout=["line1", "test"])

    class FakeSession:
        def __init__(self):
            self.active_pane = FakePane()
            self.killed = False
        def kill(self):
            self.killed = True

    class FakeServerObj:
        def new_session(self, session_name=None):
            return FakeSession()

    libtmux_mod = _make_libtmux_module(FakeServerObj())
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    close_called = []
    browser_modules = _make_browser_env_module(close_called)
    # inject parent packages and the target module
    for name, mod in browser_modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    # run check including browser checks
    check_dependencies("/some/path", check_browser=True)

    # ensure BrowserEnv.close was called
    assert close_called == [True]
