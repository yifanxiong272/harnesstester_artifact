import importlib
import sys
import types
import tempfile
import pytest

# Module under test will be imported inside each test to ensure monkeypatching of
# sys.modules (for libtmux and browser modules) takes effect.
MODULE_NAME = "openhands.runtime.impl.local.local_runtime"


def _import_module():
    return importlib.import_module(MODULE_NAME)


def test_nonexistent_path_round_041(monkeypatch):
    """When the provided code_repo_path does not exist, a ValueError is raised."""
    local_runtime = _import_module()

    # Force os.path.exists to return False for the path under test
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda p: False)

    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies("/no/such/path", check_browser=False)

    assert "does not exist" in str(exc.value)


def test_jupyter_missing_round_041(monkeypatch, tmp_path):
    """If subprocess.check_output does not return a string containing 'jupyter',
    a ValueError about Jupyter not being installed is raised."""
    local_runtime = _import_module()

    # Path exists
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda p: True)

    # Fake subprocess.check_output to return output without 'jupyter'
    def fake_check_output(*args, **kwargs):
        return "some output without the keyword"

    monkeypatch.setattr(local_runtime, "subprocess", types.SimpleNamespace(check_output=fake_check_output))

    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies(str(tmp_path), check_browser=False)

    assert "Jupyter is not properly installed" in str(exc.value)


def test_libtmux_session_error_round_041(monkeypatch, tmp_path):
    """When libtmux.Server().new_session raises, an explanatory ValueError is raised."""
    local_runtime = _import_module()

    # Path exists and jupyter check passes
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(local_runtime, "subprocess", types.SimpleNamespace(check_output=lambda *a, **k: "jupyter 1.0"))

    # Ensure code takes the non-Windows branch
    monkeypatch.setattr(local_runtime.sys, "platform", "linux", raising=False)

    # Create a fake libtmux module where Server.new_session raises
    libtmux_mod = types.ModuleType("libtmux")

    class FakeServer:
        def __init__(self):
            pass

        def new_session(self, session_name="test-session"):
            raise Exception("could not start tmux session")

    libtmux_mod.Server = FakeServer
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies(str(tmp_path), check_browser=False)

    assert "tmux is not properly installed" in str(exc.value)


def test_libtmux_pane_no_test_round_041(monkeypatch, tmp_path):
    """If libtmux is present but the captured pane output does not include 'test',
    a ValueError about libtmux is raised.
    """
    local_runtime = _import_module()

    # Path exists and jupyter check passes
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(local_runtime, "subprocess", types.SimpleNamespace(check_output=lambda *a, **k: "jupyter 1.0"))
    monkeypatch.setattr(local_runtime.sys, "platform", "linux", raising=False)

    # Build fake libtmux with a session whose pane output does NOT include 'test'
    libtmux_mod = types.ModuleType("libtmux")

    class FakePane:
        def send_keys(self, *args, **kwargs):
            pass

        def cmd(self, *args, **kwargs):
            # stdout must be a sequence; join will produce text without 'test'
            return types.SimpleNamespace(stdout=["no matching line here"])  # no 'test'

    class FakeSession:
        def __init__(self):
            self.active_pane = FakePane()
            self.killed = False

        def kill(self):
            self.killed = True

    class FakeServer:
        def __init__(self):
            pass

        def new_session(self, session_name="test-session"):
            return FakeSession()

    libtmux_mod.Server = FakeServer
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    with pytest.raises(ValueError) as exc:
        local_runtime.check_dependencies(str(tmp_path), check_browser=False)

    assert "libtmux is not properly installed" in str(exc.value)


def test_all_ok_with_browser_round_041(monkeypatch, tmp_path):
    """Full success path: jupyter present, libtmux pane contains 'test', and
    BrowserEnv.close() is invoked when check_browser=True.
    """
    local_runtime = _import_module()

    # Path exists and jupyter check returns a string containing 'jupyter'
    monkeypatch.setattr(local_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(local_runtime, "subprocess", types.SimpleNamespace(check_output=lambda *a, **k: "Jupyter 2.0"))
    monkeypatch.setattr(local_runtime.sys, "platform", "linux", raising=False)

    # Fake libtmux where the pane capture contains the word 'test'
    libtmux_mod = types.ModuleType("libtmux")

    class FakePane:
        def send_keys(self, *args, **kwargs):
            pass

        def cmd(self, *args, **kwargs):
            return types.SimpleNamespace(stdout=["some line", "test"])

    class FakeSession:
        def __init__(self):
            self.active_pane = FakePane()
            self.killed = False

        def kill(self):
            self.killed = True

    class FakeServer:
        def __init__(self):
            pass

        def new_session(self, session_name="test-session"):
            return FakeSession()

    libtmux_mod.Server = FakeServer
    monkeypatch.setitem(sys.modules, "libtmux", libtmux_mod)

    # Fake BrowserEnv module and class; record last instance so test can assert close() was called
    browser_mod = types.ModuleType("openhands.runtime.browser.browser_env")

    class BrowserEnv:
        last_instance = None

        def __init__(self):
            BrowserEnv.last_instance = self
            self.closed = False

        def close(self):
            self.closed = True

    browser_mod.BrowserEnv = BrowserEnv
    monkeypatch.setitem(sys.modules, "openhands.runtime.browser.browser_env", browser_mod)

    # Should not raise
    local_runtime.check_dependencies(str(tmp_path), check_browser=True)

    # Assert that BrowserEnv.close() was invoked
    assert BrowserEnv.last_instance is not None
    assert BrowserEnv.last_instance.closed is True
