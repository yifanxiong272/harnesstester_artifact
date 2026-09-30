import sys
import types
import pytest

from openhands.runtime.impl.local.local_runtime import check_dependencies


def _make_fake_libtmux_server(new_session_behavior):
    """Helper to create a fake libtmux module. new_session_behavior can be:
    - an Exception instance to be raised when new_session is called
    - a callable that returns a fake session object
    """

    class FakePane:
        def __init__(self, stdout_lines=None):
            self._stdout = stdout_lines or ["test"]

        def send_keys(self, *args, **kwargs):
            # no-op for tests
            return None

        def cmd(self, *args, **kwargs):
            # Return an object with a stdout attribute that is iterable
            return types.SimpleNamespace(stdout=list(self._stdout))

    class FakeSession:
        def __init__(self, pane_stdout=None):
            self.active_pane = FakePane(stdout_lines=pane_stdout)
            self.killed = False

        def kill(self):
            self.killed = True

    class FakeServer:
        def __init__(self):
            pass

        def new_session(self, session_name=None):
            if isinstance(new_session_behavior, Exception):
                raise new_session_behavior
            elif callable(new_session_behavior):
                return new_session_behavior()
            else:
                # assume iterable of stdout lines
                return FakeSession(pane_stdout=new_session_behavior)

    fake_module = types.SimpleNamespace(Server=FakeServer)
    return fake_module


def _install_fake_module(module_name, module_obj):
    """Install a fake module into sys.modules for import-time resolution."""
    sys.modules[module_name] = module_obj


def _remove_fake_module(module_name):
    sys.modules.pop(module_name, None)


def test_check_dependencies_path_missing_round_041(monkeypatch):
    """When the repo path does not exist, function raises a ValueError early.

    Covers branch: if not os.path.exists(code_repo_path) -> raise
    """
    monkeypatch.setattr("os.path.exists", lambda p: False)

    with pytest.raises(ValueError) as exc:
        check_dependencies("/some/nonexistent/path", check_browser=False)

    assert "Code repo path" in str(exc.value)


def test_check_dependencies_jupyter_missing_round_041(monkeypatch, tmp_path):
    """When jupyter check output does not contain 'jupyter', raise ValueError.

    This covers the jupyter-check branch that raises if 'jupyter' not in output.
    """
    # Path exists so the function proceeds
    monkeypatch.setattr("os.path.exists", lambda p: True)

    # Simulate subprocess.check_output returning a string without 'jupyter'
    def fake_check_output(cmd, text, cwd):
        assert text is True
        # make sure the cwd passed is the repo path provided
        assert cwd == str(tmp_path)
        return "some-tool 1.2.3\notherinfo"

    monkeypatch.setattr("subprocess.check_output", fake_check_output)

    with pytest.raises(ValueError) as exc:
        check_dependencies(str(tmp_path), check_browser=False)

    assert "Jupyter is not properly installed" in str(exc.value)


def test_check_dependencies_libtmux_session_failure_round_041(monkeypatch, tmp_path):
    """When libtmux.Server.new_session raises, the function should raise a ValueError

    Covers the branch where tmux is missing/unavailable and new_session raises.
    """
    monkeypatch.setattr("os.path.exists", lambda p: True)

    # Simulate jupyter correctly reporting itself
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, text, cwd: "Jupyter 2.0\n" if text is True else "",
    )

    # Ensure we exercise the libtmux block by pretending we're not on Windows
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    # Install fake libtmux that raises when creating a session
    fake_libtmux = _make_fake_libtmux_server(Exception("no tmux"))
    _install_fake_module("libtmux", fake_libtmux)

    try:
        with pytest.raises(ValueError) as exc:
            check_dependencies(str(tmp_path), check_browser=False)

        # The function raises a tmux-specific message
        assert "tmux is not properly installed or available on the path" in str(exc.value)
    finally:
        _remove_fake_module("libtmux")


def test_check_dependencies_all_good_with_browser_round_041(monkeypatch, tmp_path):
    """Full success path including libtmux and browser checks.

    - jupyter check passes
    - libtmux session starts and pane output contains 'test'
    - browser check is executed and BrowserEnv.close is called

    This covers branches that validate successful libtmux flow and the browser branch.
    """
    monkeypatch.setattr("os.path.exists", lambda p: True)

    # jupyter reports itself (case-insensitive check)
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda cmd, text, cwd: "JUPYTER 42\n" if text is True else "",
    )

    # Not on Windows so libtmux block runs
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    # Create a fake libtmux where capture-pane returns stdout containing 'test'
    fake_libtmux = _make_fake_libtmux_server(["line1", "test", "line3"])
    _install_fake_module("libtmux", fake_libtmux)

    # Install a fake BrowserEnv accessible as openhands.runtime.browser.browser_env
    browser_module_name = "openhands.runtime.browser.browser_env"
    browser_module = types.SimpleNamespace()

    class FakeBrowserEnv:
        closed = False

        def __init__(self):
            self._was_closed = False

        def close(self):
            FakeBrowserEnv.closed = True
            self._was_closed = True

    browser_module.BrowserEnv = FakeBrowserEnv
    _install_fake_module(browser_module_name, browser_module)

    try:
        # Call with check_browser True so BrowserEnv is constructed and closed
        check_dependencies(str(tmp_path), check_browser=True)

        # BrowserEnv.close must have been called
        assert FakeBrowserEnv.closed is True
    finally:
        _remove_fake_module("libtmux")
        _remove_fake_module(browser_module_name)
