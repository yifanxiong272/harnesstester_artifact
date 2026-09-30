import sys
import types
import pytest

from openhands.runtime.impl.local import local_runtime as lr


class FakePaneCmd:
    def __init__(self, stdout_lines):
        # stdout should be an iterable of strings
        self.stdout = stdout_lines


class FakePane:
    def __init__(self, stdout_lines):
        self._stdout = stdout_lines

    def send_keys(self, *args, **kwargs):
        # noop: simulate sending keys
        return None

    def cmd(self, *args, **kwargs):
        return FakePaneCmd(self._stdout)


class FakeSession:
    def __init__(self, pane_stdout_lines):
        self.active_pane = FakePane(pane_stdout_lines)
        self._killed = False

    def new_session(self, **kwargs):
        # not used here; Server.new_session will return a session directly
        return self

    def kill(self):
        self._killed = True


class FakeServerSuccess:
    def __init__(self, pane_stdout_lines):
        self._pane_stdout = pane_stdout_lines

    def new_session(self, session_name=None):
        return FakeSession(self._pane_stdout)


class FakeServerFailNewSession:
    def new_session(self, session_name=None):
        raise Exception("failed to create session")


def _inject_fake_libtmux(monkeypatch, server_obj):
    fake_mod = types.SimpleNamespace()
    fake_mod.Server = lambda: server_obj
    # Insert into sys.modules so `import libtmux` inside function picks it up
    monkeypatch.setitem(sys.modules, 'libtmux', fake_mod)


def _inject_fake_browser_env(monkeypatch):
    mod = types.ModuleType('openhands.runtime.browser.browser_env')

    class BrowserEnv:
        _last_instance = None

        def __init__(self):
            BrowserEnv._last_instance = self
            self.closed = False

        def close(self):
            self.closed = True

    mod.BrowserEnv = BrowserEnv
    monkeypatch.setitem(sys.modules, 'openhands.runtime.browser.browser_env', mod)
    return mod


def test_missing_path_round_041(monkeypatch):
    # Simulate code repo path missing -> triggers early ValueError
    monkeypatch.setattr('os.path.exists', lambda p: False)

    with pytest.raises(ValueError) as exc:
        lr.check_dependencies('/some/nonexistent/path', check_browser=False)

    assert '/some/nonexistent/path' in str(exc.value)
    # Ensure the project's error guidance is included
    assert 'Please follow the instructions' in str(exc.value)


def test_jupyter_missing_round_041(monkeypatch):
    # Path exists but jupyter output does not contain "jupyter" -> raise
    monkeypatch.setattr('os.path.exists', lambda p: True)

    def fake_check_output(cmd, text=True, cwd=None):
        # return output lacking the word 'jupyter'
        return 'some unrelated output'

    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    # Ensure platform is non-Windows so function proceeds to jupyter check
    monkeypatch.setattr(sys, 'platform', 'linux')

    with pytest.raises(ValueError) as exc:
        lr.check_dependencies('/some/path', check_browser=False)

    assert 'Jupyter is not properly installed' in str(exc.value)


def test_libtmux_new_session_failure_round_041(monkeypatch):
    # jupyter present, but libtmux.Server().new_session raises -> tmux error
    monkeypatch.setattr('os.path.exists', lambda p: True)

    def fake_check_output(cmd, text=True, cwd=None):
        return 'Jupyter 1.0'  # contains 'jupyter' case-insensitive

    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    monkeypatch.setattr(sys, 'platform', 'linux')

    # Inject libtmux whose Server.new_session raises
    _inject_fake_libtmux(monkeypatch, FakeServerFailNewSession())

    with pytest.raises(ValueError) as exc:
        lr.check_dependencies('/some/path', check_browser=False)

    assert 'tmux is not properly installed or available on the path' in str(exc.value)


def test_libtmux_pane_no_test_round_041(monkeypatch):
    # jupyter present, libtmux present, but pane output does not include 'test' -> raise
    monkeypatch.setattr('os.path.exists', lambda p: True)

    def fake_check_output(cmd, text=True, cwd=None):
        return 'Jupyter 2.0'  # contains 'jupyter'

    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    monkeypatch.setattr(sys, 'platform', 'linux')

    # Pane stdout missing the string 'test'
    fake_server = FakeServerSuccess(pane_stdout_lines=['no matching content'])
    _inject_fake_libtmux(monkeypatch, fake_server)

    with pytest.raises(ValueError) as exc:
        lr.check_dependencies('/some/path', check_browser=False)

    assert 'libtmux is not properly installed' in str(exc.value)


def test_all_ok_with_browser_round_041(monkeypatch):
    # Entire flow succeeds, including BrowserEnv close being called
    monkeypatch.setattr('os.path.exists', lambda p: True)

    def fake_check_output(cmd, text=True, cwd=None):
        return 'Jupyter 3.0 and jupyter lab'  # ensure 'jupyter' present

    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    monkeypatch.setattr(sys, 'platform', 'linux')

    # Pane stdout contains the word 'test'
    fake_server = FakeServerSuccess(pane_stdout_lines=['line1', 'test', 'line3'])
    _inject_fake_libtmux(monkeypatch, fake_server)

    # Inject fake BrowserEnv and observe that close() is called on the created instance
    mod = _inject_fake_browser_env(monkeypatch)

    # Should not raise
    lr.check_dependencies('/some/path', check_browser=True)

    # Confirm the BrowserEnv instance created inside the function was closed
    assert hasattr(mod.BrowserEnv, '_last_instance')
    assert mod.BrowserEnv._last_instance is not None
    assert mod.BrowserEnv._last_instance.closed is True
