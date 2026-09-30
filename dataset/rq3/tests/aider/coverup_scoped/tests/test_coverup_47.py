# file: aider/main.py:233-268
# asked: {"lines": [234, 236, 238, 239, 242, 244, 246, 248, 255, 257, 258, 260, 266, 268], "branches": [[257, 258], [257, 260]]}
# gained: {"lines": [234, 236, 238, 239, 242, 244, 246, 248, 255, 257, 258, 260, 266, 268], "branches": [[257, 258], [257, 260]]}

import sys
import types
import importlib
import pytest

def _make_streamlit_cli(captured):
    """
    Return a fake cli module whose main(args) stores args into captured list.
    """
    cli_mod = types.ModuleType("streamlit.web.cli")

    def main(args):
        # store a copy to avoid aliasing
        captured.append(list(args))
        return None

    cli_mod.main = main
    return cli_mod

def _setup_fake_gui(monkeypatch, file_path="/fake/gui.py"):
    gui_mod = types.ModuleType("aider.gui")
    gui_mod.__file__ = file_path
    monkeypatch.setitem(sys.modules, "aider.gui", gui_mod)
    return gui_mod

def _setup_streamlit_modules(monkeypatch, cli_mod):
    # Create a streamlit package and streamlit.web module that exposes cli
    streamlit_pkg = types.ModuleType("streamlit")
    web_mod = types.ModuleType("streamlit.web")
    # attach cli object on web_mod (could be a module)
    web_mod.cli = cli_mod
    # register modules in sys.modules
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_pkg)
    monkeypatch.setitem(sys.modules, "streamlit.web", web_mod)
    monkeypatch.setitem(sys.modules, "streamlit.web.cli", cli_mod)

def test_launch_gui_non_dev(monkeypatch, capsys):
    # Import the module under test
    import aider.main as aider_main

    # Prepare captures and fake modules
    captured_cli_args = []
    cli_mod = _make_streamlit_cli(captured_cli_args)
    _setup_streamlit_modules(monkeypatch, cli_mod)
    gui_mod = _setup_fake_gui(monkeypatch, file_path="/tmp/mgui.py")

    # Replace write_streamlit_credentials in aider.main with a stub that records calls
    called = {"write_called": False}
    def fake_write_streamlit_credentials():
        called["write_called"] = True
    monkeypatch.setattr(aider_main, "write_streamlit_credentials", fake_write_streamlit_credentials)

    # Ensure __version__ is non-dev
    monkeypatch.setattr(aider_main, "__version__", "1.2.3", raising=False)

    # Call launch_gui with some args
    args = ["one", "two"]
    aider_main.launch_gui(args)

    # Assertions
    # write_streamlit_credentials must have been called
    assert called["write_called"] is True

    # cli.main must have been called exactly once
    assert len(captured_cli_args) == 1
    st_args = captured_cli_args[0]

    # Build expected arguments for non-dev
    expected = [
        "run",
        gui_mod.__file__,
        "--browser.gatherUsageStats=false",
        "--runner.magicEnabled=false",
        "--server.runOnSave=false",
        "--global.developmentMode=false",
        "--server.fileWatcherType=none",
        "--client.toolbarMode=viewer",
        "--",
        *args,
    ]
    assert st_args == expected

    # Check printed output contains CONTROL-C message and does not contain "Watching for file changes."
    out = capsys.readouterr().out
    assert "CONTROL-C to exit..." in out
    assert "Watching for file changes." not in out

def test_launch_gui_dev(monkeypatch, capsys):
    # Import the module under test
    import aider.main as aider_main

    # Prepare captures and fake modules
    captured_cli_args = []
    cli_mod = _make_streamlit_cli(captured_cli_args)
    _setup_streamlit_modules(monkeypatch, cli_mod)
    gui_mod = _setup_fake_gui(monkeypatch, file_path="/var/run/gui.py")

    # Replace write_streamlit_credentials in aider.main with a stub that records calls
    called = {"write_called": False}
    def fake_write_streamlit_credentials():
        called["write_called"] = True
    monkeypatch.setattr(aider_main, "write_streamlit_credentials", fake_write_streamlit_credentials)

    # Ensure __version__ is a dev version
    monkeypatch.setattr(aider_main, "__version__", "2.0.0-dev", raising=False)

    # Call launch_gui with no extra args
    args = []
    aider_main.launch_gui(args)

    # Assertions
    # write_streamlit_credentials must have been called
    assert called["write_called"] is True

    # cli.main must have been called exactly once
    assert len(captured_cli_args) == 1
    st_args = captured_cli_args[0]

    # Build expected arguments for dev: should NOT include the production-only flags
    expected = [
        "run",
        gui_mod.__file__,
        "--browser.gatherUsageStats=false",
        "--runner.magicEnabled=false",
        "--server.runOnSave=false",
        # dev mode prints "Watching for file changes." but does not add the production flags
        "--",
        *args,
    ]
    assert st_args == expected

    # Check printed output contains both CONTROL-C and Watching message
    out = capsys.readouterr().out
    assert "CONTROL-C to exit..." in out
    assert "Watching for file changes." in out
