# file: openhands/runtime/impl/local/local_runtime.py:91-130
# asked: {"lines": [92, 93, 94, 95, 98, 99, 100, 101, 102, 104, 105, 106, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 129, 130], "branches": [[93, 94], [93, 98], [105, 106], [105, 109], [109, 110], [109, 125], [122, 123], [122, 125], [125, 0], [125, 126]]}
# gained: {"lines": [92, 93, 94, 95, 98, 99, 100, 101, 102, 104, 105, 106, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 129, 130], "branches": [[93, 94], [93, 98], [105, 106], [105, 109], [109, 110], [122, 123], [122, 125], [125, 126]]}

import types
import sys
import pytest

from openhands.runtime.impl.local.local_runtime import check_dependencies


def make_fake_libtmux_module(new_session_behavior):
    """
    new_session_behavior: a callable that returns a session or raises.
    """
    mod = types.ModuleType("libtmux")

    class FakePane:
        def __init__(self, output_lines):
            self._output = output_lines
            self.sent = []

        def send_keys(self, keys):
            self.sent.append(keys)

        def cmd(self, *args, **kwargs):
            class CmdResult:
                def __init__(self, stdout):
                    self.stdout = stdout

            return CmdResult(stdout=self._output)

    class FakeSession:
        def __init__(self, output_lines):
            self.active_pane = FakePane(output_lines)
            self.killed = False

        def kill(self):
            self.killed = True

    class FakeServer:
        def __init__(self):
            self._output_lines = None

        def new_session(self, session_name='test-session'):
            return new_session_behavior(session_name)

    mod.Server = FakeServer
    mod._FakeSession = FakeSession  # expose for potential introspection
    return mod


def make_browser_env_module():
    mod = types.ModuleType("openhands.runtime.browser.browser_env")
    mod.last_instance = None

    class BrowserEnv:
        def __init__(self):
            mod.last_instance = self
            self.closed = False

        def close(self):
            self.closed = True

    mod.BrowserEnv = BrowserEnv
    return mod


def test_nonexistent_path_raises(monkeypatch):
    # Simulate path does not exist
    monkeypatch.setattr("os.path.exists", lambda p: False)
    with pytest.raises(ValueError) as exc:
        check_dependencies("/some/fake/path", check_browser=False)
    assert "Code repo path /some/fake/path does not exist." in str(exc.value)
    assert "Please follow the instructions" in str(exc.value)


def test_jupyter_not_installed_raises(monkeypatch, tmp_path):
    # Path exists
    monkeypatch.setattr("os.path.exists", lambda p: True)
    # jupyter output missing the word 'jupyter'
    def fake_check_output(cmd, text, cwd):
        return "no relevant output"
    monkeypatch.setattr("subprocess.check_output", fake_check_output)
    with pytest.raises(ValueError) as exc:
        check_dependencies(str(tmp_path), check_browser=False)
    assert "Jupyter is not properly installed." in str(exc.value)


def test_libtmux_new_session_raises(monkeypatch, tmp_path):
    # Path exists
    monkeypatch.setattr("os.path.exists", lambda p: True)
    # jupyter present
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "jupyter 1.0")
    # ensure non-windows platform
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    # Create a libtmux where new_session raises Exception
    def raising_new_session(session_name):
        raise RuntimeError("failed to create session")

    fake_libtmux = make_fake_libtmux_module(lambda name: (_ for _ in ()).throw(RuntimeError("failed")))
    # Put into sys.modules
    monkeypatch.setitem(sys.modules, "libtmux", fake_libtmux)

    with pytest.raises(ValueError) as exc:
        check_dependencies(str(tmp_path), check_browser=False)
    assert "tmux is not properly installed or available on the path." in str(exc.value)


def test_libtmux_pane_output_missing_test_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "jupyter 1.0")
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    # new_session returns a session whose pane output does NOT contain 'test'
    def new_session_no_test(session_name):
        FakeSession = types.SimpleNamespace
        # Build an object similar to expected API
        pane = types.SimpleNamespace()
        pane.send_keys = lambda keys: None
        def cmd(*args, **kwargs):
            return types.SimpleNamespace(stdout=["nothing here"])
        pane.cmd = cmd
        session = types.SimpleNamespace(active_pane=pane, killed=False)
        def kill():
            session.killed = True
        session.kill = kill
        return session

    fake_libtmux = make_fake_libtmux_module(new_session_no_test)
    monkeypatch.setitem(sys.modules, "libtmux", fake_libtmux)

    with pytest.raises(ValueError) as exc:
        check_dependencies(str(tmp_path), check_browser=False)
    assert "libtmux is not properly installed." in str(exc.value)


def test_all_ok_with_browser_close(monkeypatch, tmp_path):
    # Path exists
    monkeypatch.setattr("os.path.exists", lambda p: True)
    # jupyter present
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: "jupyter 2.0")
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    # new_session returns a session whose pane output DOES contain 'test'
    def new_session_with_test(session_name):
        pane = types.SimpleNamespace()
        sent = []
        pane.send_keys = lambda keys: sent.append(keys)
        def cmd(*args, **kwargs):
            return types.SimpleNamespace(stdout=["some", "lines", "test"])
        pane.cmd = cmd
        session = types.SimpleNamespace(active_pane=pane, killed=False)
        def kill():
            session.killed = True
        session.kill = kill
        # expose the sent list for assertions
        session._sent = sent
        return session

    fake_libtmux = make_fake_libtmux_module(new_session_with_test)
    monkeypatch.setitem(sys.modules, "libtmux", fake_libtmux)

    # Provide fake browser env module
    fake_browser_mod = make_browser_env_module()
    monkeypatch.setitem(sys.modules, "openhands.runtime.browser.browser_env", fake_browser_mod)

    # Call with check_browser True
    check_dependencies(str(tmp_path), check_browser=True)

    # After call, ensure browser instance was created and closed
    assert getattr(fake_browser_mod, "last_instance", None) is not None
    assert fake_browser_mod.last_instance.closed is True
