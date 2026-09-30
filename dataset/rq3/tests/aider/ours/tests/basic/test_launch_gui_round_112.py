import sys
import types
import io
import contextlib
import importlib
import pytest

import aider.main as main_mod


def _make_fake_streamlit(monkeypatch):
    """Install a fake streamlit.web.cli into sys.modules and return a capture dict.

    The real code does: from streamlit.web import cli
    So we provide 'streamlit' and 'streamlit.web' modules where
    the 'streamlit.web' module has attribute 'cli' which itself is a module
    with a callable 'main'.
    """
    captured = {}

    # create modules
    top = types.ModuleType("streamlit")
    web = types.ModuleType("streamlit.web")
    cli_mod = types.ModuleType("streamlit.web.cli")

    def fake_main(args):
        # store a shallow copy so tests can assert identity/contents deterministically
        captured['args'] = list(args)

    cli_mod.main = fake_main
    # attach cli module as attribute of web package
    web.cli = cli_mod
    top.web = web

    # inject into sys.modules so imports inside launch_gui find them
    monkeypatch.setitem(sys.modules, 'streamlit', top)
    monkeypatch.setitem(sys.modules, 'streamlit.web', web)
    # Note: 'from streamlit.web import cli' will resolve web.cli
    return captured


def _inject_fake_aider_gui(monkeypatch, filename='fake_gui.py'):
    """Ensure 'aider.gui' submodule exists in sys.modules with a predictable __file__."""
    fake_gui = types.ModuleType('aider.gui')
    fake_gui.__file__ = filename
    monkeypatch.setitem(sys.modules, 'aider.gui', fake_gui)
    return fake_gui


def test_launch_gui_dev_round_112(monkeypatch):
    """Dev mode ("-dev" in __version__) should hit the is_dev branch and not add prod flags.

    Assertions:
    - write_streamlit_credentials is called once
    - printed output contains CONTROL-C and the Watching message
    - cli.main receives expected st_args without production flags
    """
    captured = _make_fake_streamlit(monkeypatch)

    # record calls to write_streamlit_credentials
    called = []

    # Patch the write_streamlit_credentials in the module under test
    monkeypatch.setattr(main_mod, 'write_streamlit_credentials', lambda: called.append(True))

    # Ensure the function will treat this as a dev build
    monkeypatch.setattr(main_mod, '__version__', '2.0.0-dev')

    # Inject a fake aider.gui submodule so the local import in launch_gui finds it
    _inject_fake_aider_gui(monkeypatch, filename='fake_gui.py')

    # Call launch_gui and capture stdout
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main_mod.launch_gui(['one', 'two'])

    out = buf.getvalue()

    # Basic prints are present
    assert "CONTROL-C to exit..." in out
    # Dev-specific print should appear
    assert "Watching for file changes." in out
    # write_streamlit_credentials should have been invoked exactly once
    assert called == [True]

    # Validate what was passed into the fake cli.main
    assert 'args' in captured, "cli.main was not invoked"
    expected = [
        'run',
        'fake_gui.py',
        '--browser.gatherUsageStats=false',
        '--runner.magicEnabled=false',
        '--server.runOnSave=false',
        '--',
        'one',
        'two',
    ]
    assert captured['args'] == expected


def test_launch_gui_prod_round_112(monkeypatch):
    """Non-dev mode should hit the else branch and append production flags.

    Assertions:
    - write_streamlit_credentials is called
    - produced st_args include the production-only flags
    - the Watching message is NOT present
    """
    captured = _make_fake_streamlit(monkeypatch)

    called = []
    monkeypatch.setattr(main_mod, 'write_streamlit_credentials', lambda: called.append(True))

    # Non-dev version string (no '-dev')
    monkeypatch.setattr(main_mod, '__version__', '2.0.0')

    # Inject a fake aider.gui submodule so the local import in launch_gui finds it
    _inject_fake_aider_gui(monkeypatch, filename='fake_gui.py')

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main_mod.launch_gui(['alpha'])

    out = buf.getvalue()

    assert "CONTROL-C to exit..." in out
    # Should NOT print the dev-only watching message
    assert "Watching for file changes." not in out
    # write_streamlit_credentials called
    assert called == [True]

    assert 'args' in captured, "cli.main was not invoked"
    expected = [
        'run',
        'fake_gui.py',
        '--browser.gatherUsageStats=false',
        '--runner.magicEnabled=false',
        '--server.runOnSave=false',
        '--global.developmentMode=false',
        '--server.fileWatcherType=none',
        '--client.toolbarMode=viewer',
        '--',
        'alpha',
    ]
    assert captured['args'] == expected
